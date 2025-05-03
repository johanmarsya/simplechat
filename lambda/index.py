import json
import os
import urllib.request
import urllib.error
import re

# Lambda コンテキストからリージョンを抽出する関数（今回は使用しないが、コードの互換性のために残す）
def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

# FastAPIエンドポイントのURL（環境変数から取得）
API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://617f-34-124-225-91.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # FastAPI用のリクエストペイロードを構築
        # SimpleGenerationRequest スキーマに適合
        user_message = messages[-1]["content"]  # 最後のユーザーメッセージを取得
        request_payload = {
            "prompt": user_message,
            "max_new_tokens": 512,
            "do_sample": True,  # サンプリングを有効化（仮定）
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        print("Calling FastAPI endpoint with payload:", json.dumps(request_payload))
        
        # FastAPIエンドポイントにPOSTリクエストを送信
        req = urllib.request.Request(
            API_ENDPOINT,
            data=json.dumps(request_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                response_body = json.loads(response.read().decode('utf-8'))
                print("FastAPI response:", json.dumps(response_body, default=str))
                
                # 応答の検証
                if not response_body.get('response'):
                    raise Exception("No response content from the FastAPI endpoint")
                
                # アシスタントの応答を取得
                assistant_response = response_body['response']
                
                # アシスタントの応答を会話履歴に追加
                messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                
                # 成功レスポンスの返却
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                        "Access-Control-Allow-Methods": "OPTIONS,POST"
                    },
                    "body": json.dumps({
                        "success": True,
                        "response": assistant_response,
                        "conversationHistory": messages
                    })
                }
                
        except urllib.error.HTTPError as e:
            error_message = f"HTTP Error {e.code}: {e.reason}"
            print("HTTP Error:", error_message)
            raise Exception(error_message)
        except urllib.error.URLError as e:
            error_message = f"URL Error: {str(e.reason)}"
            print("URL Error:", error_message)
            raise Exception(error_message)
            
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }