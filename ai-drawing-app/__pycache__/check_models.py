import os
import google.generativeai as genai

# 環境変数からAPIキーを読み込む
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

print("--- あなたのAPIキーで利用可能なモデル一覧 ---")
for m in genai.list_models():
    # 画像やテキストを生成できるモデルだけを絞り込んで表示
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
        