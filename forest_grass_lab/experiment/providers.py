"""四种原生 HTTP 格式；保留完整原生历史，不增加隐含 prompt 或自动重试。"""
import base64
import copy
import json
import os
import httpx


def read_chat_stream(response, record=None):
    """Reassemble native chat deltas, retaining reasoning and tool arguments."""
    if 'application/json' in response.headers.get('content-type', ''):
        response.read()
        if record is not None:
            record['body'] = response.text
        return response.json()
    message = {'role': 'assistant', 'content': ''}
    choice = {'index': 0, 'message': message, 'finish_reason': None}
    result = {'choices': [choice], '_stream_chunks': []}
    calls = {}
    pending = []

    def event(data):
        if data == '[DONE]':
            return
        chunk = json.loads(data)
        result['_stream_chunks'].append(chunk)
        if chunk.get('error'):
            raise ValueError('Streaming API error: ' + json.dumps(chunk['error']))
        for key in ('id', 'model', 'created', 'system_fingerprint', 'usage'):
            if chunk.get(key) is not None:
                result[key] = chunk[key]
        for item in chunk.get('choices') or []:
            if item.get('index', 0) != 0:
                raise ValueError('Only one completion is supported')
            if item.get('finish_reason'):
                choice['finish_reason'] = item['finish_reason']
            delta = item.get('delta') or {}
            for key, value in delta.items():
                if key == 'tool_calls' or value is None:
                    continue
                if key == 'role':
                    message[key] = value
                elif isinstance(value, str):
                    message[key] = message.get(key, '') + value
                else:
                    raise ValueError('Unsupported streaming field: ' + key)
            for part in delta.get('tool_calls') or []:
                call = calls.setdefault(part['index'], {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}})
                if part.get('id'):
                    call['id'] += part['id']
                if part.get('type'):
                    call['type'] = part['type']
                for key in ('name', 'arguments'):
                    call['function'][key] += (part.get('function') or {}).get(key) or ''

    for line in response.iter_lines():
        if record is not None:
            record.setdefault('stream_lines', []).append(line)
        if line.startswith('data:'):
            pending.append(line[5:].lstrip())
        elif not line and pending:
            event('\n'.join(pending))
            pending.clear()
    if pending:
        event('\n'.join(pending))
    if not choice['finish_reason']:
        raise ValueError('Chat stream ended without finish_reason; output is incomplete')
    if calls:
        message['tool_calls'] = [calls[i] for i in sorted(calls)]
    return result


class Session:
    def __init__(self, config, prompt, transport=None):
        self.config, self.prompt = config, prompt
        self.provider = config['provider']
        self.key = os.environ.get(config.get('api_key_env', ''), '')
        if not self.key and transport is None:
            raise ValueError(f'未设置密钥环境变量 {config.get("api_key_env")}')
        self.client = httpx.Client(timeout=config.get('timeout_seconds', 300), transport=transport)
        self.history = []
        self.request = self.response = self.error_response = None
        self.observe(prompt['user'], prompt['images'])

    def observe(self, text, images=()):
        """Append real local PNGs as native image inputs, never as path-only text."""
        blocks = []
        for path in images:
            data = base64.b64encode(path.read_bytes()).decode('ascii')
            if self.provider == 'openai':
                blocks.append(dict(type='input_image', image_url=f'data:image/png;base64,{data}'))
            elif self.provider == 'openai_chat':
                blocks.append(dict(type='image_url', image_url={'url': f'data:image/png;base64,{data}'}))
            elif self.provider == 'anthropic':
                blocks.append(dict(type='image', source=dict(type='base64', media_type='image/png', data=data)))
            elif self.provider == 'gemini':
                blocks.append(dict(inlineData=dict(mimeType='image/png', data=data)))
        if self.provider == 'gemini':
            parts = [{'text': text}] + blocks
            if self.history and self.history[-1].get('role') == 'user':
                self.history[-1]['parts'].extend(parts)
            else:
                self.history.append(dict(role='user', parts=parts))
        elif self.provider in ('openai', 'openai_chat', 'anthropic'):
            kind = 'input_text' if self.provider == 'openai' else 'text'
            content = [dict(type=kind, text=text)] + blocks
            if self.provider == 'anthropic' and self.history and self.history[-1].get('role') == 'user':
                self.history[-1]['content'].extend(content)
            else:
                self.history.append(dict(role='user', content=content))
        else:
            raise ValueError('provider 必须为 openai/openai_chat/anthropic/gemini')

    def payload(self):
        c, p = self.config, self.provider
        model = c['model']
        tokens = c.get('max_output_tokens', 16384)
        tools = self.prompt['tools']
        if p == 'openai':
            base = c.get('base_url', 'https://api.openai.com/v1')
            replay = c.get('responses_replay', 'full')
            if replay not in ('full', 'visible'):
                raise ValueError('responses_replay must be full or visible')
            history = copy.deepcopy(self.history)
            if replay == 'visible':
                # Configured relay compatibility; retain raw history in the trace.
                history = [item for item in history if item.get('type') != 'reasoning']
                for item in history:
                    item.pop('id', None)
                    item.pop('status', None)
            body = dict(model=model, instructions=self.prompt['system'], input=history,
                        max_output_tokens=tokens, store=False)
            if replay == 'full':
                body['include'] = ['reasoning.encrypted_content']
            if tools:
                body['tools'] = [dict(type='function', **t, strict=False) for t in tools]
                body['parallel_tool_calls'] = False
            headers = {'Authorization': f'Bearer {self.key}'}
            suffix = '/responses'
        elif p == 'openai_chat':
            base = c.get('base_url', 'https://api.openai.com/v1')
            body = dict(model=model, messages=[dict(role='system', content=self.prompt['system'])] + copy.deepcopy(self.history),
                        **{c.get("max_tokens_field", "max_completion_tokens"): tokens})
            if c.get("stream"):
                body.update(stream=True, stream_options={"include_usage": True})
            if tools:
                body['tools'] = [dict(type='function', function=t) for t in tools]
            headers = {'Authorization': f'Bearer {self.key}'}
            suffix = '/chat/completions'
        elif p == 'anthropic':
            base = c.get('base_url', 'https://api.anthropic.com/v1')
            body = dict(model=model, system=self.prompt['system'], messages=copy.deepcopy(self.history), max_tokens=tokens)
            if tools:
                body['tools'] = [dict(name=t['name'], description=t['description'], input_schema=t['parameters']) for t in tools]
            headers = {'x-api-key': self.key, 'anthropic-version': '2023-06-01'}
            suffix = '/messages'
        else:
            base = c.get('base_url', 'https://generativelanguage.googleapis.com/v1beta')
            body = dict(systemInstruction={'parts': [{'text': self.prompt['system']}]},
                        contents=copy.deepcopy(self.history), generationConfig=dict(maxOutputTokens=tokens))
            if tools:
                body['tools'] = [dict(functionDeclarations=[dict(name=t['name'], description=t['description'], parametersJsonSchema=t['parameters']) for t in tools])]
            headers = {'x-goog-api-key': self.key}
            suffix = f'/models/{model}:generateContent'
        # 型号特定推理/采样选项原样提供；调用者在 models.json 中固定。
        body.update(copy.deepcopy(c.get('parameters', {})))
        return base.rstrip('/') + suffix, headers, body

    def record_response(self, response):
        # Only response metadata; never store authentication headers.
        self.error_response = dict(status_code=response.status_code,
            content_type=response.headers.get('content-type'),
            request_id=response.headers.get('x-request-id') or response.headers.get('request-id'))

    def next(self):
        self.request = self.response = self.error_response = None
        url, headers, body = self.payload()
        self.request = body
        # Log actual input only; authentication headers never enter the log.
        if self.config.get('log_api_input', True):
            print(f'[API input] {self.provider} {self.config["model"]}', flush=True)
            print(json.dumps(body, ensure_ascii=False, indent=2), flush=True)
        if self.provider == 'openai_chat' and body.get('stream'):
            with self.client.stream('POST', url, headers=headers, json=body) as response:
                self.record_response(response)
                if response.is_error:
                    response.read()
                    self.error_response['body'] = response.text
                response.raise_for_status()
                data = read_chat_stream(response, self.error_response)
        else:
            response = self.client.post(url, headers=headers, json=body)
            self.record_response(response)
            self.error_response['body'] = response.text
            response.raise_for_status()
            data = response.json()
        self.response = data
        text, calls = [], []
        if self.provider == 'openai':
            items = data.get('output', [])
            self.history.extend(copy.deepcopy(items))  # 含 reasoning/encrypted_content
            for item in items:
                if item.get('type') == 'function_call':
                    calls.append(dict(id=item['call_id'], name=item['name'], arguments=item['arguments']))
                for block in item.get('content', []):
                    if block.get('type') == 'output_text':
                        text.append(block['text'])
            finish = data.get('status')
            usage = data.get('usage', {})
        elif self.provider == 'openai_chat':
            choice = data['choices'][0]
            message = choice['message']
            self.history.append(copy.deepcopy(message))
            text.append(message.get('content') or '')
            for item in message.get('tool_calls', []):
                calls.append(dict(id=item['id'], name=item['function']['name'], arguments=item['function']['arguments']))
            finish, usage = choice.get('finish_reason'), data.get('usage', {})
        elif self.provider == 'anthropic':
            content = data.get('content', [])
            self.history.append(dict(role='assistant', content=copy.deepcopy(content)))  # 保留 thinking 签名
            for item in content:
                if item['type'] == 'text':
                    text.append(item['text'])
                elif item['type'] == 'tool_use':
                    calls.append(dict(id=item['id'], name=item['name'], arguments=item['input']))
            finish, usage = data.get('stop_reason'), data.get('usage', {})
        else:
            candidate = data.get('candidates', [{}])[0]
            content = candidate.get('content', dict(role='model', parts=[]))
            self.history.append(copy.deepcopy(content))  # 不拆掉 functionCall 的 thoughtSignature
            for i, item in enumerate(content.get('parts', [])):
                if item.get('text') and not item.get('thought', False):
                    text.append(item['text'])
                if 'functionCall' in item:
                    f = item['functionCall']
                    calls.append(dict(id=f.get('id'), name=f['name'], arguments=f.get('args', {})))
            finish, usage = candidate.get('finishReason'), data.get('usageMetadata', {})
        self.error_response = None
        return dict(text='\n'.join(text), calls=calls, finish=finish, usage=usage)

    def results(self, values):
        if self.provider == 'openai':
            self.history.extend(dict(type='function_call_output', call_id=c['id'], output=json.dumps(r, ensure_ascii=False)) for c, r in values)
        elif self.provider == 'openai_chat':
            self.history.extend(dict(role='tool', tool_call_id=c['id'], content=json.dumps(r, ensure_ascii=False)) for c, r in values)
        elif self.provider == 'anthropic':
            self.history.append(dict(role='user', content=[dict(type='tool_result', tool_use_id=c['id'],
                content=json.dumps(r, ensure_ascii=False), is_error=not r.get('ok', True)) for c, r in values]))
        else:
            parts = []
            for c, r in values:
                item = dict(name=c['name'], response=r)
                if c['id']:
                    item['id'] = c['id']
                parts.append(dict(functionResponse=item))
            self.history.append(dict(role='user', parts=parts))

    def close(self):
        self.client.close()
