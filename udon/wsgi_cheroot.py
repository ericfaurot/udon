import bottle
import cheroot.server
import cheroot.wsgi

import udon.wsgi


class Gateway_10b(cheroot.wsgi.Gateway_10):
    def get_environ(self):
        env = super().get_environ()
        env['udon.connection'] = self.req.conn._udon_conn
        return env
cheroot.wsgi.wsgi_gateways[1,0] = Gateway_10b


class CherootConnection(cheroot.server.HTTPConnection):

    _udon_conn = None

    def close(self):
        self._udon_conn.closed()
        super().close()


class CherootServer(bottle.ServerAdapter):
    def run(self, handler):
        conn_factory = self.options.pop('conn_factory', None)
        options = {}
        options.update(self.options)
        options['bind_addr'] = self.host, self.port
        options['wsgi_app'] = handler
        server = cheroot.wsgi.Server(**options)
        def _connection(*args, **kwargs):
            conn = CherootConnection(*args, **kwargs)
            conn._udon_conn = conn_factory(conn)
            return conn
        server.ConnectionClass = _connection
        try:
            server.start()
        finally:
            server.stop()
