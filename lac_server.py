import json
import os

import tornado
import tornado.ioloop
import tornado.web
from tornado.options import define, options

from pylac.tag import LacTagger

base_dir = os.path.abspath(os.path.dirname(__file__))

define('port', default=8888, help='port', type=int)

tagger = LacTagger(os.path.join(base_dir, 'conf'), '/usr/local/lib', 99999)
tagger.init()


class LacHandler(tornado.web.RequestHandler):
    def post(self, *args, **kwargs):
        try:
            data = json.loads(self.request.body)
            line = data['text'].encode('utf-8')
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps(dict(status=1, error=e), indent=4))
        else:
            words = tagger.tagging(line)
            self.write(json.dumps(dict(status=0, words=words),
                                  ensure_ascii=False, indent=4))


def make_app():
    return tornado.web.Application(
        handlers=[
            (r'/lac/v1/tag', LacHandler, dict())
        ]
    )


if __name__ == '__main__':
    options.parse_command_line()
    app = make_app()
    app.listen(options.port)
    try:
        tornado.ioloop.IOLoop.current().start()
    except Exception:
        tornado.ioloop.IOLoop.current().stop()
    finally:
        tagger.close()
