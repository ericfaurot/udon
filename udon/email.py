#
# Copyright (c) 2019 Eric Faurot <eric@faurot.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
import email
import email.header
import email.message



class ErrorMixin:
    errors = ()

    def add_error(self, error):
        self.errors += (error, )


class Header(ErrorMixin):

    def __init__(self, name, raw):
        self.name = name
        self.raw = raw
        assert isinstance(raw, str)
        self.value = raw
        try:
            raw.encode('utf-8')
        except UnicodeEncodeError:
            self.add_error('has-surrogates')
            self.value = raw.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')

    @property
    def decoded(self):
        return self.decode()

    def decode(self, unfold = True, strip = True):
        def _decode(s, e):
            if isinstance(s, bytes):
                s = s.decode(e or 'ascii')
            return s
        value = self.value
        if value and unfold:
            value = value.replace('\n', '').replace('\r', '')
        if value:
            value = ''.join(_decode(s, e) for (s, e) in email.header.decode_header(value))
        if value and strip:
            value = ' '.join(value.strip().split())
        return value


class Part(ErrorMixin):

    raw = None
    body = None
    headers = ()
    children = ()

    def get_header(self, name):
        for header in self.get_all_headers(name):
            return header

    def get_all_headers(self, name):
        for header in self.headers:
            if name.lower() == header.name.lower():
                yield header

    def walk(self):
        def _iter(part, ancestors):
            yield part, ancestors
            for child in part.children:
                for res in _iter(child, ancestors + (part, )):
                    yield res
        return _iter(self, ())


class Message(Part):

    @classmethod
    def from_bytes(kls, data):
        msg = email.message_from_bytes(data)
        return kls.from_message(msg)

    @classmethod
    def from_message(kls, msg):

        def _build_part(part, node):
            part.raw = node
            part.headers = tuple(Header(name, raw) for name, raw in node._headers)

            payload = node.get_payload(decode = True)
            if isinstance(payload, bytes):
                try:
                    body = payload.decode(node.get_content_charset('latin-1'))
                except UnicodeDecodeError:
                    part.add_error('payload-encoding')
                    body = payload.decode('latin-1')
                part.body = body

            if node.is_multipart():
                part.children = tuple(_build_part(Part(), child) for child in node.get_payload())
            return part

        return _build_part(kls(), msg)
