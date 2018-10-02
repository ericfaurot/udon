#
# Copyright (c) 2018 Eric Faurot <eric@faurot.net>
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

import heapq


class PriorityQueue(object):

    def __init__(self):
        self.heap = []

    def __len__(self):
        return len(self.heap)

    def __bool__(self):
        return bool(self.heap)

    def insert(self, item, priority):
        heapq.heappush(self.heap, (priority, item))

    def peek(self):
        priority, item = self.heap[0]
        return item, priority

    def pull(self):
        priority, item = heapq.heappop(self.heap)
        return item, priority

    def __iter__(self):
        while self.heap:
            priority, item = heapq.heappop(self.heap)
            yield item, priority

    def pull_until(self, priority_max):
        while self.heap:
            priority, item = self.heap[0]
            if priority > priority_max:
                break
            heapq.heappop(self.heap)
            yield item, priority


class DoublyLinkedList(object):

    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def _remove_node(self, node):
        if node is self.head:
            self.head = node[1]
        else:
            node[0][1] = node[1]
        if node is self.tail:
            self.tail = node[0]
        else:
            node[1][0] = node[0]
        self.size -= 1

    def _insert_node_between(self, node, node_prev, node_next):
        if node_prev is None:
            self.head = node
        else:
            node[0] = node_prev
            node_prev[1] = node

        if node_next is None:
            self.tail = node
        else:
            node[1] = node_next
            node_next[0] = node
        self.size += 1

    def __len__(self):
        return self.size

    def __bool__(self):
        return bool(self.size)

    def peek_head(self):
        return self.head[2]

    def pop_head(self):
        node = self.head
        self._remove_node(node)
        return node[2]

    def pop_head_n(self, count):
        for _ in range(count):
            if not self.head:
                break
            yield self.pop_head()

    def peek_tail(self):
        return self.tail[2]

    def pop_tail(self):
        node = self.tail
        self._remove_node(node)
        return node[2]

    def pop_tail_n(self, count):
        for _ in range(count):
            if not self.tail:
                break
            yield self.pop_tail()

    def remove(self, node):
        self._remove_node(node)

    def insert_after(self, elt, node_prev):
        node = [ None, None, elt ]
        self._insert_node_between(node, node_prev, node_prev[1])
        return node

    def insert_before(self, elt, node_next):
        node = [ None, None, elt ]
        self._insert_node_between(node, node_next[0], node_next)
        return node

    def insert_head(self, elt):
        node = [ None, None, elt ]
        self._insert_node_between(node, None, self.head)
        return node

    def insert_tail(self, elt):
        node = [ None, None, elt ]
        self._insert_node_between(node, self.tail, None)
        return node

    def __iter__(self):
        node = self.head
        while node:
            yield node[2]
            node = node[1]
