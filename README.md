# CloudFoundry API Crawler

Crawling CloudFoundry API site for swagger 2.0

## Getting Started

### Prerequisites

* [Python 3.x](https://www.python.org/downloads/)

### Installing

First, clone git project.

```
git clone https://github.com/usolkim/cf-api-crawler.git
```

And then install required modules for python.

```
pip install beautifulsoup4
pip install requests
```

That's OK. You can crawling now.

```
python cf-api-crawler.py
```

### Configuration

You can configuration by config.json.

```
{
  "requests":{
    "proxy": {
      "http": "http://proxy:port",
      "https": "http://proxy:port"
    },
    "verify": "/path/to/certfile"
  },
  "cf": {
    "api_version": "2.5.0",
    "auth": {
      "type": "oauth2",
      "flow": "password",
      "tokenUrl": "https://login.cf.domain/oauth/token"
    }
  },
  "output_file" : "/path/to/output/swagger.json"
}
```
* requests.proxy : optional. Refer to the [doc](http://docs.python-requests.org/en/master/user/advanced/#proxies)
* requests.verify : optional. Refer to the [doc](http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification)
* cf.api_version : optional. default is latest version
* cf.auth : optional. default is None
* output_file : optional. deafult is swagger.json

## Authors

* **USol Kim** - [usolkim](https://github.com/usolkim)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

