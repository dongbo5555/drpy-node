"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'JavXX',
  lang: 'hipy'
})
"""

import gzip
import json
import re
import sys
import base64
import time
import os
from urllib.parse import unquote, urlparse
import requests

try:
    from pyquery import PyQuery as pq
    HAS_PYQUERY = True
except ImportError:
    try:
        from lxml import html as lxml_html
        HAS_LXML = True
    except ImportError:
        HAS_LXML = False
    HAS_PYQUERY = False
    pq = None

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend='{}'): pass
        def getName(self): pass
        def isVideoFormat(self, url): pass
        def manualVideoCheck(self): pass
        def destroy(self): pass
        def log(self, msg): print(f"[JavXX] {msg}")

class Spider(Spider):

    def init(self, extend='{}'):
        try:
            config = json.loads(extend)
            self.proxies = config.get('proxy', {})
            self.plp = config.get('plp', '')
            
            # 如果配置中没有代理，尝试环境变量
            if not self.proxies:
                http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
                https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
                
                if http_proxy or https_proxy:
                    self.proxies = {
                        'http': http_proxy,
                        'https': https_proxy or http_proxy
                    }
                    self.log(f"使用环境变量代理: {self.proxies}")
                    
            # 设置请求超时
            self.timeout = 15
            
        except Exception as e:
            self.log(f"初始化配置失败: {e}")
            self.proxies = {}
            self.plp = ''
            self.timeout = 15

    def getName(self):
        return "JavXX"

    def isVideoFormat(self, url):
        video_extensions = ['.mp4', '.m3u8', '.avi', '.mov', '.wmv', '.flv', '.webm']
        return any(url.lower().endswith(ext) for ext in video_extensions)

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    host = 'https://javxx.com'
    contr = 'cn'
    conh = f'{host}/{contr}'

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'referer': f'{conh}/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    # 分类和过滤器数据
    gcate = 'H4sIAAAAAAAAA6tWejan4dm0DUpWCkp5qeVKOkrPm9e+nL4CxM/ILwHygfIv9k8E8YtSk1PzwELTFzxf0AgSKs0DChXnF6WmwIWfbW55OWcTqqRuTmpiNljN8427n3asBsmmp+YVpRaDtO2Z8nTiDJBQYnIJUKgYLPq0Y9uTvXOeTm0DSeQCdReBRJ9vBmqfDhIqTi3KhGhf0P587T6QUElierFSLQCk4MAf0gAAAA=='
    flts = 'H4sIAAAAAAAAA23QwYrCMBAG4FeRnH0CX0WKBDJiMRpoY0WkIOtFXLQU1IoEFFHWw4qHPazgii/TRPctNKK1Ro/zz8cM/PkmKkMD5TLIZQ5HWVTFFUiNHqY1PeebyNOxAxSwCwWCOWitMxmEcttW0VKJKfKzN4kJAfLk1O9OdmemKzF+B8f2+j9aPVacEdwoeDbU3TuJd93LgdPXx1F8PmAdoEwNqTaBDFemrLAqL72hSnReqcuvDkgCRUsGkfqenw59AxaxxxybP9uRuFjkW5reai7alIOTKjoJzKoxpUnDvWG8bcnlj/obyHCcKi95JxeTeN9LEcu3zoYr9GndAQAA'
    actft = 'H4sIAAAAAAAAA22UTUsbURSG/0qYtQMxZvIhIvidxI/oVpEy6GiCmpFkEhEpVBcqikYprV2kG6EkhYK2XRbxzziT+C88c2/onLnnunznec47zJ3LWTsydpxDYzRhVJzqdsUzhoyavecoD1r2bjN8snZktEIwPJI0h0fSoRqL/vW33p9/xsehyLLgcZ4sETUrDcNp6pJRt2A4TV0yapYFwxZ1yahbMGxRl4yalYHhDHXJqFswnKEuGTUrC8NZ6pJRt2A4S10yalYOhnPUJaNuwXCOumTUrDwM56lLRrTWQ29wNzaa+7GLIRO/FRPYM9F7+hV8f6D3TCKZ5GQKyRQn00imOZlBMsPJLJJZTuaQzHFSQFLgpIikyEkJSYmTeSTxzHNSQFLgpIikyEkJSYmTeSTznCwgWeBkEckiJ0tIljgpIylzsoxkmZMVJCucrCJZRRL/9/a2E/v3MvF/H14cLBlLpJL+32OqTyXNVHTJRFCxZaaiYREUDMuFVo0IKrZM2jEiKBjWCS0XEVRsmbRVRFAwLBBaJyIoGHZCPpoeT2TkZ8fPruHW4xt1EPnpCTyo8buf/ZsreseG26x5CPvd09f72+DL4+tZmxTP3bQPP7SqzkEDxZf/F8Hdj373pNe5JPHAcXZ2mRk8tP3bn9zcc2te5R016JzrasMTnrMZiZ1Pfvsu+H3ff75m4pbdcutVT3W/dsAND279DSxD8pmOBgAA'

    def get_with_retry(self, url, params=None, max_retries=3, delay=1):
        """带重试机制的请求"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    proxies=self.proxies, 
                    timeout=self.timeout,
                    verify=False  # 部分证书可能有问题
                )
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                self.log(f"请求超时 ({attempt+1}/{max_retries}): {url}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
            except requests.exceptions.ProxyError:
                self.log(f"代理错误 ({attempt+1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
            except Exception as e:
                self.log(f"请求失败 ({attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
        return None

    def homeContent(self, filter):
        try:
            response = self.get_with_retry(f"{self.conh}")
            if response:
                data = self.getpq(response.text)
            else:
                return {'class': [], 'filters': {}, 'list': []}
        except Exception as e:
            self.log(f"首页请求失败: {e}")
            return {'class': [], 'filters': {}, 'list': []}
            
        result = {}
        try:
            cate = self.ungzip(self.gcate)
            classes = []
            filters = {}
            for k, j in cate.items():
                classes.append({
                    'type_name': k,
                    'type_id': j
                })
                if j == 'actresses':
                    fts = self.ungzip(self.actft)
                else:
                    fts = self.ungzip(self.flts)
                filters[j] = fts
            result['class'] = classes
            result['filters'] = filters
            result['list'] = self.getvl(self._find_elements(data, '.vid-items .item'))
        except Exception as e:
            self.log(f"首页数据处理失败: {e}")
            result = {'class': [], 'filters': {}, 'list': []}
            
        return result

    def homeVideoContent(self):
        return {}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        try:
            if tid in ['genres', 'makers', 'series', 'tags']:
                gggg = tid if tid == 'series' else tid[:-1]
                pagecount = 1
                response = self.get_with_retry(f"{self.conh}/{tid}")
                if response:
                    data = self.getpq(response.text)
                else:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
                    
                for i in data(f'.term-items.{gggg} .item').items():
                    videos.append({
                        'vod_id': i('a').attr('href'),
                        'vod_name': i('h2').text(),
                        'vod_remarks': i('.meta').text(),
                        'vod_tag': 'folder',
                        'style': {"type": "rect", "ratio": 2}
                    })
            elif tid == 'actresses':
                params = {
                    'height': extend.get('height'),
                    "cup": extend.get('cup'),
                    "sort": extend.get('sort'),
                    'age': extend.get('age'),
                    "page": pg
                }
                c_params = {k: v for k, v in params.items() if v}
                response = self.get_with_retry(f"{self.conh}/{tid}", c_params)
                if response:
                    data = self.getpq(response.text)
                else:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
                    
                pagecount = self.getpgc(data('ul.pagination li').eq(-1))
                for i in data('.chanel-items .item').items():
                    i = i('.main')
                    videos.append({
                        'vod_id': i('.info a').attr('href'),
                        'vod_name': i('.info h2').text(),
                        'vod_pic': i('.avatar img').attr('src'),
                        'vod_year': i('.meta div div').eq(-1).text(),
                        'vod_remarks': i('.meta div div').eq(0).text(),
                        'vod_tag': 'folder',
                        'style': {"type": "oval", "ratio": 0.75}
                    })
            else:
                tid = tid.split('_click')[0].replace(f"/{self.contr}/", "")
                params = {
                    "filter": extend.get('filter'),
                    "sort": extend.get('sort'),
                    "page": pg
                }
                c_params = {k: v for k, v in params.items() if v}
                response = self.get_with_retry(f"{self.conh}/{tid}", c_params)
                if response:
                    data = self.getpq(response.text)
                else:
                    return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
                    
                videos = self.getvl(data('.vid-items .item'))
                pagecount = self.getpgc(data('ul.pagination li').eq(-1))
                
        except Exception as e:
            self.log(f"分类内容获取失败: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
            
        result = {}
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = pagecount
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        try:
            response = self.get_with_retry(f"{self.host}{ids[0]}")
            if not response:
                return {'list': []}
                
            data = self.getpq(response.text)
        except Exception as e:
            self.log(f"详情页请求失败: {e}")
            return {'list': []}
            
        try:
            dv = self._find_elements(data, '#video-details')
            pnpn = {
                '老僧酿酒、名妓读经': f"{self._get_text(data, '#video-info h1')}${self._get_attr(data, '#video-files div', 'data-url')}",
                '书生玩剑': '#'.join(
                    [f"{self._get_text(i, '.info .title span', -1)}$_gggb_{self._get_attr(i, '.info .title', 'href')}" for i in
                     self._find_elements(data, '.main .vid-items .item')]),
                '将军作文': '#'.join([f"{self._get_text(i, '.info .title span', -1)}$_gggb_{self._get_attr(i, '.info .title', 'href')}" for i in
                                  self._find_elements(data, '.vid-items.side .item')])
            }
            n, p = [], []
            for k, v in pnpn.items():
                if v and v != 'None$None' and not v.startswith('None$_gggb_'):
                    n.append(k)
                    p.append(v)
                    
            if not n:
                return {'list': []}
                
            vod = {
                'vod_content': self._get_text(dv, '.content'),
                'vod_play_from': '$$$'.join(n),
                'vod_play_url': '$$$'.join(p)
            }
            
            # 提取视频基本信息
            code = ""
            publish_date = ""
            duration = ""
            actors = []
            makers = []
            tags = []
            genres = []
            
            for i in self._find_elements(dv, '.meta div'):
                label_text = self._get_text(i, 'label')
                if re.search(r'代碼|代码', label_text):
                    code = self._get_text(i, 'span')
                elif re.search(r'發布日期|发布日期', label_text):
                    publish_date = self._get_text(i, 'span')
                    vod['vod_year'] = publish_date.split('-')[0] if publish_date else ''
                elif re.search(r'時長|时长', label_text):
                    duration = self._get_text(i, 'span')
                elif re.search(r'演員|演员', label_text):
                    for j in self._find_elements(i, 'a'):
                        actors.append(self._get_text(j, ''))
                elif re.search(r'製作商|制作商', label_text):
                    for j in self._find_elements(i, 'a'):
                        makers.append(self._get_text(j, ''))
                elif re.search(r'標籤|标签', label_text):
                    for j in self._find_elements(i, 'a'):
                        tags.append(self._get_text(j, ''))
                elif re.search(r'類別|类别', label_text):
                    for j in self._find_elements(i, 'a'):
                        genres.append(self._get_text(j, ''))
            
            # 构建详细的信息描述
            info_lines = []
            if code:
                info_lines.append(f"代码: {code}")
            if publish_date:
                info_lines.append(f"发布日期: {publish_date}")
            if duration:
                info_lines.append(f"时长: {duration}")
            if actors:
                info_lines.append(f"演员: {', '.join(actors)}")
            if makers:
                info_lines.append(f"制作商: {', '.join(makers)}")
            if tags:
                info_lines.append(f"标签: {', '.join(tags)}")
            if genres:
                info_lines.append(f"类别: {', '.join(genres)}")
            
            # 将详细信息添加到内容中
            if info_lines:
                vod['vod_content'] = '\n'.join(info_lines) + '\n\n' + (vod['vod_content'] if vod['vod_content'] else '')
            
            # 设置演员和导演信息
            if actors:
                vod['vod_actor'] = ', '.join(actors)
            if makers:
                vod['vod_director'] = ', '.join(makers)
            
            return {'list': [vod]}
        except Exception as e:
            self.log(f"详情数据处理失败: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            params = {'keyword': key, 'page': pg}
            response = self.get_with_retry(f"{self.conh}/search", params)
            if not response:
                return {'list': [], 'page': pg}
                
            data = self.getpq(response.text)
            return {'list': self.getvl(self._find_elements(data, '.vid-items .item')), 'page': pg}
        except Exception as e:
            self.log(f"搜索失败: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        self.log(f"开始获取播放内容，id: {id[:50]}...")
        
        try:
            # 处理_gggb_开头的ID
            if id.startswith('_gggb_'):
                try:
                    video_url = f"{self.host}{id.replace('_gggb_', '')}"
                    self.log(f"获取视频详情: {video_url}")
                    
                    response = self.get_with_retry(video_url)
                    if not response:
                        raise ValueError("无法获取视频详情")
                        
                    data = self.getpq(response.text)
                    id = self._get_attr(data, '#video-files div', 'data-url')
                    if not id:
                        raise ValueError("无法获取视频数据URL")
                        
                    self.log(f"获取到加密URL: {id[:50]}...")
                except Exception as e:
                    self.log(f"获取视频详情失败: {e}")
                    return {'parse': 0, 'url': '', 'header': {}}
            
            # 解密URL
            try:
                url = self.de_url(id)
                parsed_url = urlparse(url)
                video_id = parsed_url.path.split('/')[-1]
                
                self.log(f"解密URL成功: {url[:100]}...")
                self.log(f"视频ID: {video_id}")
                
                tkid = self.encrypt_video_id(video_id)
                self.log(f"加密后的token: {tkid[:50]}...")
            except Exception as e:
                self.log(f"URL解密失败: {e}")
                # 尝试直接使用id作为播放地址
                if id.startswith('http'):
                    self.log("使用原始ID作为播放地址")
                    return {
                        'parse': 0,
                        'url': id,
                        'header': {
                            'user-agent': self.headers['user-agent'],
                            'referer': f"{self.host}/"
                        }
                    }
                return {'parse': 0, 'url': '', 'header': {}}
            
            # 多个播放服务器配置
            play_servers = [
                "https://surrit.store",
                "https://surrit.xyz", 
                "https://surrit.cc",
                "https://surrit.cloud",
                "https://surrit.work",
                "https://surrit.net",
                "https://surrit.top",
                "https://surrit.org"
            ]
            
            play_url = None
            server_used = None
            
            for server in play_servers:
                try:
                    api_url = f"{server}/stream?src=javxx&poster=&token={tkid}"
                    self.log(f"尝试服务器: {server}")
                    
                    # 为每个服务器使用不同的超时设置
                    response = requests.get(
                        api_url, 
                        timeout=10, 
                        proxies=self.proxies,
                        verify=False,
                        headers={
                            'user-agent': self.headers['user-agent'],
                            'accept': 'application/json',
                            'referer': server
                        }
                    )
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            self.log(f"服务器响应: {data.get('code', 'unknown')}")
                            
                            if data.get("result", {}).get("media"):
                                decrypted_media = self.decrypt_media(data["result"]["media"])
                                decrypted_data = json.loads(decrypted_media)
                                play_url = decrypted_data.get("stream")
                                
                                if play_url:
                                    self.log(f"成功获取播放地址")
                                    server_used = server
                                    break
                            else:
                                self.log("响应中没有media字段")
                        except json.JSONDecodeError:
                            self.log("响应不是有效的JSON")
                        except Exception as e:
                            self.log(f"解析响应失败: {e}")
                    else:
                        self.log(f"服务器返回状态码: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    self.log(f"服务器 {server} 连接超时")
                    continue
                except requests.exceptions.ProxyError:
                    self.log(f"代理连接失败，尝试直接连接")
                    # 尝试不使用代理
                    try:
                        response = requests.get(
                            api_url, 
                            timeout=10,
                            verify=False,
                            headers={
                                'user-agent': self.headers['user-agent'],
                                'accept': 'application/json'
                            }
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("result", {}).get("media"):
                                decrypted_media = self.decrypt_media(data["result"]["media"])
                                decrypted_data = json.loads(decrypted_media)
                                play_url = decrypted_data.get("stream")
                                if play_url:
                                    self.log(f"直接连接成功获取播放地址")
                                    server_used = server
                                    break
                    except Exception as e:
                        self.log(f"直接连接也失败: {e}")
                        continue
                except Exception as e:
                    self.log(f"服务器 {server} 失败: {str(e)[:100]}")
                    continue
            
            # 备用方案1：使用原始解密URL
            if not play_url:
                self.log("所有服务器失败，尝试使用原始解密URL")
                if url and self.isVideoFormat(url):
                    play_url = url
                    server_used = "direct"
                else:
                    # 备用方案2：尝试从视频页面直接提取
                    try:
                        # 根据视频ID构建可能的直链
                        video_hosts = [
                            "https://video.javxx.com",
                            "https://cdn.javxx.com",
                            "https://stream.javxx.com"
                        ]
                        
                        for host in video_hosts:
                            test_url = f"{host}/videos/{video_id}.mp4"
                            self.log(f"测试直链: {test_url}")
                            
                            # 快速检查URL是否可达
                            try:
                                head_resp = requests.head(test_url, timeout=5, proxies=self.proxies)
                                if head_resp.status_code < 400:
                                    play_url = test_url
                                    server_used = host
                                    self.log(f"直链可用: {test_url}")
                                    break
                            except:
                                continue
                    except Exception as e:
                        self.log(f"备用方案也失败: {e}")
            
            if not play_url:
                self.log("所有播放方案都失败")
                return {'parse': 0, 'url': '', 'header': {}}
            
            # 设置播放头信息
            headers = {
                'user-agent': self.headers['user-agent'],
                'accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5'
            }
            
            if server_used:
                headers.update({
                    'origin': server_used,
                    'referer': f"{server_used}/"
                })
            else:
                headers.update({
                    'referer': f"{self.host}/"
                })
            
            self.log(f"最终播放地址: {play_url[:100]}...")
            return {
                'parse': 0,
                'url': play_url,
                'header': headers
            }
            
        except Exception as e:
            self.log(f"播放内容获取失败: {traceback.format_exc()}")
            return {'parse': 0, 'url': '', 'header': {}}

    def encrypt_video_id(self, video_id, key=None):
        try:
            if key is None:
                key = "ym1eS4t0jTLakZYQ"
            
            key_bytes = key.encode('utf-8')
            encrypted_bytes = []
            
            for i, char in enumerate(video_id):
                key_byte = key_bytes[i % len(key_bytes)]
                encrypted_byte = ord(char) ^ key_byte
                encrypted_bytes.append(encrypted_byte)
            
            encrypted_base64 = base64.b64encode(bytes(encrypted_bytes)).decode('utf-8')
            return encrypted_base64
        except Exception as e:
            self.log(f"视频ID加密失败: {e}")
            return ""

    def decrypt_media(self, encrypted_media, key="ym1eS4t0jTLakZYQ"):
        try:
            encrypted_bytes = base64.b64decode(encrypted_media)
            
            key_bytes = key.encode('utf-8')
            decrypted_chars = []
            
            for i, byte in enumerate(encrypted_bytes):
                key_byte = key_bytes[i % len(key_bytes)]
                decrypted_char = byte ^ key_byte
                decrypted_chars.append(chr(decrypted_char))
            
            decrypted_text = ''.join(decrypted_chars)
            url_decoded_text = unquote(decrypted_text)
            return url_decoded_text
        except Exception as e:
            self.log(f"媒体数据解密失败: {e}")
            return "{}"

    def de_url(self, encoded_str):
        try:
            decoded = base64.b64decode(encoded_str).decode()
            key = "G9zhUyphqPWZGWzZ"
            result = []
            for i, char in enumerate(decoded):
                key_char = key[i % len(key)]
                decrypted_char = chr(ord(char) ^ ord(key_char))
                result.append(decrypted_char)
            return unquote(''.join(result))
        except Exception as e:
            self.log(f"URL解密失败: {e}")
            return ""

    def localProxy(self, param):
        return {}

    def liveContent(self, url):
        return {}

    def getvl(self, data):
        videos = []
        try:
            for i in self._iterate_elements(data):
                img = self._find_elements(i, '.img')
                imgurl = self._get_attr(img, '.image img', 'src')
                if imgurl:
                    imgurl = imgurl.replace("/s360/", "/s1080/")
                    
                videos.append({
                    'vod_id': self._get_attr(img, 'a', 'href'),
                    'vod_name': self._get_text(i, '.info .title'),
                    'vod_pic': imgurl,
                    'vod_year': self._get_text(i, '.info .meta div', -1),
                    'vod_remarks': self._get_text(i, '.duration'),
                    'style': {"type": "rect", "ratio": 1.33}
                })
        except Exception as e:
            self.log(f"视频列表处理失败: {e}")
            
        return videos

    def getpgc(self, data):
        try:
            if data is not None:
                if hasattr(data, 'attr') and data('a'):
                    href = data('a').attr('href')
                    if href:
                        return int(href.split('page=')[-1])
                text = data.text() if hasattr(data, 'text') else str(data)
                if text and text.isdigit():
                    return int(text)
            return 1
        except Exception as e:
            self.log(f"获取页数失败: {e}")
            return 1

    def ungzip(self, data):
        try:
            result = gzip.decompress(base64.b64decode(data)).decode()
            return json.loads(result)
        except Exception as e:
            self.log(f"解压数据失败: {e}")
            return {}

    def getpq(self, data):
        if HAS_PYQUERY:
            try:
                return pq(data)
            except Exception as e:
                self.log(f"PyQuery解析失败: {e}")
        
        if HAS_LXML:
            try:
                return lxml_html.fromstring(data)
            except Exception as e:
                self.log(f"lxml解析失败: {e}")
        
        self.log("使用备用解析方式")
        return SimpleHTMLParser(data)

    def _find_elements(self, data, selector):
        if data is None:
            return []
            
        if HAS_PYQUERY and hasattr(data, '__call__'):
            return data(selector)
        elif HAS_LXML and hasattr(data, 'xpath'):
            return data.xpath(selector)
        else:
            return getattr(data, 'find', lambda x: [])(selector)

    def _get_attr(self, element, selector, attr):
        if element is None:
            return None
            
        try:
            if HAS_PYQUERY and hasattr(element, 'attr'):
                target = element(selector) if selector else element
                return target.attr(attr) if target else None
            elif HAS_LXML and hasattr(element, 'xpath'):
                target = element.xpath(selector)[0] if selector else element
                return target.get(attr) if target is not None else None
            else:
                return getattr(element, 'get_attr', lambda x, y: None)(selector, attr)
        except:
            return None

    def _get_text(self, element, selector, index=None):
        if element is None:
            return ""
            
        try:
            if HAS_PYQUERY and hasattr(element, 'text'):
                target = element(selector) if selector else element
                if index is not None and hasattr(target, 'eq'):
                    target = target.eq(index)
                return target.text() if target else ""
            elif HAS_LXML and hasattr(element, 'xpath'):
                target = element.xpath(selector) if selector else [element]
                if index is not None and target:
                    target = [target[index]] if index < len(target) else []
                return ' '.join([elem.text_content().strip() for elem in target]) if target else ""
            else:
                return getattr(element, 'get_text', lambda x: "")(selector)
        except:
            return ""

    def _iterate_elements(self, data):
        if data is None:
            return []
            
        if hasattr(data, 'items'):
            return data.items()
        elif hasattr(data, '__iter__') and not isinstance(data, str):
            return data
        else:
            return [data]

class SimpleHTMLParser:
    def __init__(self, html_text):
        self.html = html_text
        self._elements = []
        
    def __call__(self, selector):
        return SimpleHTMLParser(self.html)
        
    def items(self):
        return [self]
        
    def attr(self, name):
        if name == 'href':
            match = re.search(r'href=[\'"]([^\'"]+)[\'"]', self.html)
            return match.group(1) if match else None
        elif name == 'src':
            match = re.search(r'src=[\'"]([^\'"]+)[\'"]', self.html)
            return match.group(1) if match else None
        return None
        
    def text(self):
        return re.sub(r'<[^>]+>', '', self.html).strip()