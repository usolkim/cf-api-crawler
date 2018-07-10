from bs4 import BeautifulSoup
import requests
import re
import json

class CF_Api_Crawler:
  def __init__(self, configFile = 'config.json'):
    with open(configFile, 'r') as f:
        config = json.load(f)
    self.config = config
    self.domain = "https://apidocs.cloudfoundry.org"

  def _config(self, config_path, default = None):
    # default = kwargs.get('default', None)
    if config_path is None or len(config_path) == 0:
      return default
    paths = config_path.split('.')
    obj = self.config
    for path in paths :
      if path in obj:
        obj = obj[path]
      else:
        return default
    return obj

  def _get(self, url):
    res = requests.get(url, proxies=self._config("requests.proxy"), verify=self._config("requests.verify"))
    return BeautifulSoup(res.content, 'html.parser')

  def _url(self, path):
    if path is None:
      return self.domain
    if not path.startswith('/'):
      return self.domain + '/' + path
    return self.domain + path

  def crawling(self):
    soup = self._get(self._url(self._config("cf.api_version")))
    api_version = soup.find_all('div')[0].button.strong.next_sibling.strip()
    swagger_json = self._create_swagger_json(api_version)

    for item in soup.find('div', class_='container').find_all('a', href=lambda x: x and re.compile('.html$').search(x)) :
      self._parse_item(swagger_json['paths'], item)

    return swagger_json

  def _purify_path(self, path):
    if not path.startswith('/'):
      path = '/'+path

    path = path.replace('?', '')

    if path.endswith('/'):
      path = path[0:len(path)-1]
    return path

  def _parse_item(self, paths_obj, item):
    html_url = self._url(item['href'])
    print("Start crawling from " + html_url)

    item_obj = self._get(html_url)

    container = item_obj.find('div', class_='container')

    title = self._text(container.h1)
    article = container.find('div', class_='article')
    summary = self._text(article.h2)

    strs = self._text(article.h3).split(' ')
    method = strs[0].lower()
    path = self._purify_path(strs[1])

    path_param_regex = re.compile(':(\\w*)')
    path_params = path_param_regex.findall(path)

    path = path_param_regex.sub(self._path_param_rep, path)

    if paths_obj.get(path) is None:
      path_obj = {}
    else:
      path_obj = paths_obj[path]

    path_obj['x-swagger-router-controller'] = 'controller'

    method_obj = {
      'tags': [ title ],
      'summary': summary,
      'produces': ['application/json']
    }

    if re.compile('deprecated').match(summary.lower()):
      method_obj['deprecated'] = True

    if article.find('p', class_='explanation') is not None :
      method_obj['description'] = self._desc(article.find('p', class_='explanation'))

    method_obj['parameters'] = []

    _path_param = lambda name:{
      'name': name,
      'in': 'path',
      'required': True,
      'type': 'string'
    }

    for param_name in path_params:
      method_obj['parameters'].append(_path_param(param_name))

    if article.find('table', class_='parameters') is not None:
      for param in article.find('table', class_='parameters').find('tbody').find_all('tr', class_=lambda x: x != 'deprecated'):
        if self._text(param.find(class_='name')) in path_params:
          continue
        method_obj['parameters'].append(self._query_param(param))

    if method in ['put', 'post']:
      req_body = self._req_body(article)
      if req_body is not None:
        method_obj['parameters'].append(req_body)

    if article.find('pre', class_='response status') is not None:
      res_statuses = self._text(article.find('pre', class_='response status')).split(' ')
      method_obj['responses'] = {
        res_statuses[0]: {
          'description': res_statuses[1]
        }
      }
    else:
      method_obj['responses'] = {
        '200': {
          'description': 'OK'
        }
      }

    path_obj[method] = method_obj
    paths_obj[path] = path_obj

  def _req_body(self, div):
    h4 = div.find('h4', string='Body')
    if h4 is None:
      return None
    table = h4.next_element.next_element.next_element

    if table.name == 'table' and 'fields' in table.attrs['class']:
      body = {
        'name': 'body',
        'in': 'body',
        'schema': {
          'properties':{
          }
        }
      }

      required = []

      for tr in table.find('tbody').find_all('tr', class_=lambda x: x != 'deprecated'):
        tds = tr.find_all('td')
        name = self._text(tds[0].find('span'))

        if self._required(tds[0].find('span')):
          required.append(name)

        desc = self._text(tds[1].find('span'))

        prop = {
          'description': desc,
        }

        self._enum(tds[3], prop)

        example_values = tds[4].find_all('li')
        if example_values != []:
          prop['example'] = self._text(example_values[0]).replace('\"', '\\\"')

        body['schema']['properties'][name] = prop

      if required != []:
        body['schema']['required'] = required

      return body

  def _path_param_rep(self, match):
    p = match.group()
    return '{' + p[1:len(p)] + '}'

  def _query_param(self, tr_soap_obj):
    tds_soap_obj = tr_soap_obj.find_all('td')
    name = self._text(tds_soap_obj[0].find('span'))

    param = {
      'name': name,
      'in': 'query',
      'description': self._text(tds_soap_obj[1].find('span'))
    }

    param['required'] = self._required(tds_soap_obj[0].find('span'))

    if name in ['page', 'results-per-page']:
      param['type'] = 'integer'
    else:
      param['type'] = 'string'

    self._enum(tds_soap_obj[2], param)

    return param

  def _required(self, obj):
    p = obj.parent
    if p.has_attr('class') and 'required' in p['class']:
      return True
    else:
      return False

  def _enum(self, td_soap_obj, parent_obj):
    valid_values = td_soap_obj.find_all('li')
    if valid_values != []:
      parent_obj['enum'] = []
      for valid_value in valid_values:
        parent_obj['enum'].append(self._text(valid_value))

  def _text(self, obj):
    return obj.text.strip()

  def _desc(self, soap_obj):
    desc_strs = self._text(soap_obj).split('\n')
    desc = '';
    for desc_str in desc_strs :
        if desc_str.strip() == '':
            continue
        desc = (desc + ' ' + desc_str.strip()).strip()
    return desc.replace('. ', '.\n').replace('\"', '\\\"')

  def _create_swagger_json(self, api_version):
    swagger_json = {
      'swagger': '2.0',
      'info': {
        'title': 'Cloud Foundry API Swagger Site',
        'version': api_version
      },
      'externalDocs': {
        'description': 'Official Cloud Foundry API Spec Site',
        'url': 'https://apidocs.cloudfoundry.org'
      },
      'paths': {}
    }
    if self._config("cf.auth") is not None :
      swagger_json['securityDefinitions'] = {
        'auth': self._config("cf.auth")
      }
      swagger_json['security'] = [
        {'auth': []}
      ]
    return swagger_json

  def export(self, swagger_json):
    with open(self._config("output_file", default="swagger.json"), 'w') as output_file:
      json.dump(swagger_json, output_file, indent = 2, ensure_ascii=False, separators=(',',':'))

def main():
    crawler = CF_Api_Crawler()

    swagger_json = crawler.crawling()
    crawler.export(swagger_json)
            
if __name__ == '__main__':
    main()