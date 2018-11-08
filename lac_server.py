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


class LacWordcut(tornado.web.RequestHandler):
    def post(self, *args, **kwargs):
        try:
            data = json.loads(self.request.body)
            line = data['text'].encode('utf-8')
        except Exception as e:
            self.set_status(400)
            self.write(json.dumps(dict(success=False, error=str(e)), indent=4))
        else:
            try:
                words = tagger.tagging(line)
                self.write(json.dumps(dict(success=True, words=words),
                                      ensure_ascii=False, indent=4))
            except Exception as e:
                self.set_status(500)
                self.write(
                    json.dumps(dict(success=False, error=str(e)), indent=4))


def make_app():
    return tornado.web.Application([
        (r'/lac/v1/tag', LacWordcut, dict())
    ])


if __name__ == '__main__':
    options.parse_command_line()
    app = make_app()
    app.listen(options.port)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.current().stop()
    finally:
        tagger.close()
