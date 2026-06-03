import os
import io
import json
import base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image, ImageDraw  # ImageDrawを追加

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

@app.post("/api/inspect-drawing")
async def inspect_drawing(
    file: UploadFile = File(...),
    custom_rules: str = Form(""),
    manual: UploadFile = File(None)
):
    try:
        import fitz  # ループ内でのインポートを維持
        contents = await file.read()
        
        # 1. 図面の画像化（PDF/画像両対応）
        if file.filename.lower().endswith(".pdf"):
            doc = fitz.open(stream=contents, filetype="pdf")
            page = doc.load_page(0)
            mat = fitz.Matrix(2.0, 2.0)  # 高解像度化
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            doc.close()
        elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="PDFまたは画像ファイルのみ対応しています。")

        # 画面表示用のオリジナル画像Base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # 2. マニュアルPDFのテキスト抽出
        manual_text = ""
        if manual and manual.filename.lower().endswith(".pdf"):
            manual_contents = await manual.read()
            manual_doc = fitz.open(stream=manual_contents, filetype="pdf")
            for m_page in manual_doc:
                manual_text += m_page.get_text()
            manual_doc.close()
        
        # 3. AIへのプロンプト
        prompt = f"""
        # あなたの役割
        熟練の機械設計エンジニアとして図面を厳格に審査し、結果をJSON形式のみで返答してください。
        エラー位置のバウンディングボックス[ymin, xmin, ymax, xmax]（0〜1000で正規化）を必ず含めてください。

        ※重要：box_2dの座標は、エラーが発生している「文字」や「該当する寸法線」のエリアだけを厳密にピンポイントで四角く囲んでください。縦横の座標を絶対に入れ替えないこと。

        # 【適用ルール】
        ■ 標準項目: {custom_rules}
        ■ 社内固有ルール: {manual_text if manual_text else "特になし"}

        # 出力JSONフォーマット
        {{
            "title_block": {{
                "status": "OK または NG",
                "details": "エラー概要",
                "advice": "NGの論理的理由と具体的な修正案。OKは空文字",
                "box_2d": [ymin, xmin, ymax, xmax] または []
            }},
            "dimensions": {{
                "status": "OK または NG",
                "details": "エラー概要",
                "advice": "NGの論理的理由と具体的な修正手順。OKは空文字",
                "box_2d": [ymin, xmin, ymax, xmax] または []
            }},
            "overall_result": "合格 または 不合格"
        }}
        """

        model = genai.GenerativeModel('gemini-3.5-flash')
        response = model.generate_content([prompt, image], generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        result_json = json.loads(response.text)
        
        # 4. 【確実版】AIが見た画像そのものに赤枠を直接描画してPDF化する
        # これにより、PDF内部の「回転」や「原点のズレ」のバグを100%回避します
        # 編集用にオリジナルのコピーを作成
        output_image = image.copy()
        draw = ImageDraw.Draw(output_image)
        img_w, img_h = output_image.size

        def draw_error_on_image(box2d, label_text):
            if box2d and len(box2d) == 4:
                ymin, xmin, ymax, xmax = box2d
                # 0〜1000の座標を、実際の画像ピクセルサイズに変換
                left = (xmin / 1000) * img_w
                top = (ymin / 1000) * img_h
                right = (xmax / 1000) * img_w
                bottom = (ymax / 1000) * img_h
                
                # 赤枠を描画（線幅を太めの5ピクセルにして見やすく）
                draw.rectangle([left, top, right, bottom], outline=(231, 76, 60), width=5)
                # エラーラベルを挿入
                draw.text((left + 5, top + 5), label_text, fill=(231, 76, 60))

        if result_json["title_block"]["status"] == "NG":
            draw_error_on_image(result_json["title_block"]["box_2d"], "NG: TITLE BLOCK")
        if result_json["dimensions"]["status"] == "NG":
            draw_error_on_image(result_json["dimensions"]["box_2d"], "NG: DIMENSIONS")

        # 赤枠を描き終えた画像をPDFに変換して出力
        output_pdf_buffer = io.BytesIO()
        output_image.save(output_pdf_buffer, format="PDF")
        pdf_base64 = base64.b64encode(output_pdf_buffer.getvalue()).decode("utf-8")

        return {
            "success": True, 
            "data": result_json,
            "image_base64": img_base64,
            "pdf_base64": pdf_base64
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"サーバー内部エラー: {str(e)}")