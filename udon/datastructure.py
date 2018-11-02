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


class PriorityQueue:

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

    def pop(self):
        priority, item = heapq.heappop(self.heap)
        return item, priority

    def pop_until(self, priority_max):
        while self.heap:
            priority, item = self.heap[0]
            if priority > priority_max:
                break
            heapq.heappop(self.heap)
            yield item, priority

    def __iter__(self):
        while self.heap:
            priority, item = heapq.heappop(self.heap)
            yield item, priority


_UNDEFINED = object()
class DListNode:

    __slots__ = "prev", "next", "item"

    def __init__(self, item = _UNDEFINED):
        if item is not _UNDEFINED:
            self.item = item

    def remove(self):
        self.prev.next = self.next
        self.next.prev = self.prev

    def insert_before(self, node):
        self.next = node
        self.prev = prev = node.prev
        prev.next = node.prev = self

    def insert_after(self, node):
        self.prev = node
        self.next = next = node.next
        next.prev = node.next = self


class DoublyLinkedList:

    def __init__(self, entries = ()):
        self.head = DListNode()
        self.tail = DListNode()
        self.head.next = self.tail
        self.tail.prev = self.head
        self.size = 0
        for entry in entries:
            self.insert_tail(entry)

    def _remove_node(self, node):
        node.remove()
        self.size -= 1

    def __len__(self):
        return self.size

    def __bool__(self):
        return bool(self.size)

    def peek_head(self):
        try:
            return self.head.next.item
        except AttributeError:
            raise IndexError("peek from empty doubly-linked list")

    def pop_head(self):
        node = self.head.next
        if node is self.tail:
            raise IndexError("pop from empty doubly-linked list")
        self._remove_node(node)
        return node.item

    def pop_head_n(self, count):
        for _ in range(count):
            try:
                yield self.pop_head()
            except IndexError:
                break

    def peek_tail(self):
        try:
            return self.tail.prev.item
        except AttributeError:
            raise IndexError("peek from empty doubly-linked list")

    def pop_tail(self):
        node = self.tail.prev
        if node is self.head:
            raise IndexError("pop from empty doubly-linked list")
        self._remove_node(node)
        return node.item

    def pop_tail_n(self, count):
        for _ in range(count):
            try:
                yield self.pop_tail()
            except IndexError:
                break

    def remove(self, node):
        self._remove_node(node)

    def insert_after(self, entry, node_prev):
        node = DListNode(entry)
        node.insert_after(node_prev)
        self.size += 1
        return node

    def insert_before(self, entry, node_next):
        node = DListNode(entry)
        node.insert_before(node_next)
        self.size += 1
        return node

    def insert_head(self, entry):
        return self.insert_after(entry, self.head)

    def insert_tail(self, entry):
        return self.insert_before(entry, self.tail)

    def __iter__(self):
        node = self.head.next
        while node is not self.tail:
            yield node.item
            node = node.next

    def __reversed__(self):
        node = self.tail.prev
        while node is not self.head:
            yield node.item
            node = node.prev
