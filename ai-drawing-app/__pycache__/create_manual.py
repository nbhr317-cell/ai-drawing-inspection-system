import fitz  # PyMuPDF

def create_test_manual():
    # 新しいPDFドキュメントを作成
    doc = fitz.open()
    page = doc.new_page()
    
    # テスト用のマニュアル内容（AIに判定させたい独自ルール）
    manual_content = """【A社 標準製図マニュアル・特記仕様書】

1. 管理項目の厳格化（表題欄ルール）
・図面番号（図番）の末尾には、必ず改訂番号として「-A」または「-B」を付与すること。
  （例：DWG-2026-001-A はOK、DWG-2026-001 はNGとする）
・当社の標準製品においては、材質（Material）に「AL（アルミ）」を使用することは原則禁止とする。
  必ず「SUS304」または「S45C」のいずれかを指定すること。

2. 寸法配置の優先順位（二重寸法ルール）
・正面図、平面図、側面図の間で寸法が重複（二重寸法）している場合、必ず「正面図」に記載されている寸法を正とする。
・重複が発見された場合は、設計者に対して「側面図または平面図の寸法線を削除し、正面図に集約せよ」と具体的な修正指示を出すこと。

3. 特記事項
・すべての寸法公差はJIS B 0405の「中級（m）」を適用する。
・図面右下の設計者欄には、姓だけでなく「フルネーム」で記載すること。
"""

    # PDFにテキストを書き込む（日本語フォントを指定して文字化けを防ぐ）
    # Windowsに標準搭載されている「MSゴシック」を使用します
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, manual_content, fontname="msgothic", fontsize=12)
    
    # PDFファイルとして保存
    output_filename = "test_manual.pdf"
    doc.save(output_filename)
    doc.close()
    print(f"成功: {output_filename} を作成しました！")

if __name__ == "__main__":
    create_test_manual()