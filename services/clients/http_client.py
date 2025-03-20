import json
import logging
import os
from typing import Any, Dict

import requests


class HttpClient:
    @staticmethod
    def post(url: str, data: Dict[str, any], headers: Dict[str, any] = None) -> requests.Response:
        response = requests.post(url=url, data=data, headers=headers)
        response.raise_for_status()
        return response
    
    
def search_query(query: str, headers: Dict[str, Any] = None) -> list:
    base_url = os.getenv("SPIDER_API_URL")
    if not base_url:
        print("Error: SPIDER_API_URL environment variable is not set.")
        return []

    url = f"{base_url}/search"
    headers = headers or {"Content-Type": "application/json"}
    data = {"query": query}
    
    try:
        response = HttpClient.post(url=url, data=json.dumps(data), headers=headers)
        response.raise_for_status()  # 确保请求成功
        
        # 解析响应数据
        response_json = response.json()
        return response_json.get("success", [])
    
    except requests.exceptions.HTTPError as err:
        logging.error(f"query: {query} HTTPError: {err}")
        if response is not None:
            logging.error(f"Response content: {response.text}")
        return []  # 返回空列表或者你可以选择抛出异常
        
    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException: {e}")
        return []  # 请求错误时返回空列表
    
    except Exception as ex:
        logging.error(f"An unexpected error occurred: {ex}")
        return []  # 未知错误时返回空列表
    
    
def sync_workflow_request(app_id: str, features: dict):
    api_token = os.getenv("CONSUMER_API_TOKEN")
    url_prefix = os.getenv("CONSUMER_API_PREFIX") + "/admin/apps/workflow/sync"
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json; charset=UTF-8'  # 指定编码为 UTF-8
    }
    body = {
        "app_id": app_id,
        "features": features,
    }
    response = requests.post(url_prefix, json=body, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)
        
def delete_conversation(conversation_id: str):
    api_token = os.getenv("CONSUMER_API_TOKEN")
    api_prefix = os.getenv("CONSUMER_API_PREFIX")
    url_prefix =  f"{api_prefix}/admin/apps/delete/conversation/{conversation_id}"
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json; charset=UTF-8'  # 指定编码为 UTF-8
    }
    response = requests.delete(url_prefix, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)
