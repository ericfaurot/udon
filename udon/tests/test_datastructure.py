import unittest

import udon.datastructure


class TestDoublyLinkedList(unittest.TestCase):

    def make_list(self, entries = ()):
        return udon.datastructure.DoublyLinkedList(entries)

    def test_empty(self):
        self.assertEqual(len(self.make_list([])), 0)

    def test_size(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(len(lst), len(elements))

    def test_iter(self):
        elements = list(range(10))
        self.assertEqual(elements, list(self.make_list(elements)))

    def test_peek_head(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(lst.peek_head(), elements[0])
        self.assertEqual(len(lst), len(elements))

    def test_peek_head_empty(self):
        with self.assertRaises(IndexError):
            self.make_list().peek_head()

    def test_pop_head(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(lst.pop_head(), elements[0])
        self.assertEqual(len(lst), len(elements) - 1)

    def test_pop_head_empty(self):
        with self.assertRaises(IndexError):
            self.make_list().pop_head()

    def test_pop_head_n(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(list(lst.pop_head_n(3)), elements[:3])
        self.assertEqual(len(lst), len(elements) - 3)

    def test_pop_head_n_0(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(list(lst.pop_head_n(0)), [])
        self.assertEqual(len(lst), len(elements))

    def test_pop_head_n_overflow(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(list(lst.pop_head_n(50)), elements)
        self.assertEqual(len(lst), 0)

    def test_peek_tail(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(lst.peek_tail(), elements[-1])
        self.assertEqual(len(lst), len(elements))

    def test_peek_tail_empty(self):
        with self.assertRaises(IndexError):
            self.make_list().peek_tail()

    def test_pop_tail(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(lst.pop_tail(), elements[-1])
        self.assertEqual(len(lst), len(elements) - 1)

    def test_pop_tail_empty(self):
        with self.assertRaises(IndexError):
            self.make_list().pop_tail()

    def test_pop_tail_n(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(list(lst.pop_tail_n(3)), list(reversed(elements[-3:])))
        self.assertEqual(len(lst), len(elements) - 3)

    def test_pop_tail_n_0(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(list(lst.pop_tail_n(0)), [])
        self.assertEqual(len(lst), len(elements))

    def test_pop_tail_n_overflow(self):
        elements = list(range(10))
        lst = self.make_list(elements)
        self.assertEqual(list(lst.pop_tail_n(50)), list(reversed(elements)))
        self.assertEqual(len(lst), 0)

    def test_insert(self):
        lst = udon.datastructure.DoublyLinkedList()
        node = { c: lst.insert_tail(c) for c in "bcegh" }
        lst.insert_before("a", node['b'])
        lst.insert_after("i", node['h'])
        lst.insert_before("d", node['e'])
        lst.insert_after("f", node['e'])
        self.assertEqual("".join(lst), "abcdefghi")


class TestPriorityQueue(unittest.TestCase):

    def make_queue(self, entries = ()):
        prioq = udon.datastructure.PriorityQueue()
        for priority, entry in enumerate(entries):
            prioq.insert(entry, priority)
        return prioq

    def test_empty(self):
        self.assertEqual(len(self.make_queue()), 0)

    def test_size(self):
        elements = list("abcdefghijk")
        self.assertEqual(len(self.make_queue(elements)), len(elements))

    def test_iter(self):
        elements = list("abcdefghijk")
        result = [ entry for entry, prio in self.make_queue(elements) ]
        self.assertEqual(result, elements)

    def test_insert(self):
        elements = list("abcdeghijk")
        prioq = self.make_queue(elements)
        prioq.insert('f', 4.5)
        result = [ entry for entry, prio in prioq ]
        self.assertEqual(result, list("abcdefghijk"))

    def test_peek(self):
        elements = list("abcdeghijk")
        prioq = self.make_queue(elements)
        self.assertEqual(prioq.peek(), ("a", 0))
        self.assertEqual(len(prioq), len(elements))

    def test_peek_empty(self):
        with self.assertRaises(IndexError):
            self.make_queue().peek()

    def test_pop(self):
        elements = list("abcdeghijk")
        prioq = self.make_queue(elements)
        self.assertEqual(prioq.pop(), ("a", 0))
        self.assertEqual(len(prioq), len(elements) - 1)

    def test_pop_empty(self):
        with self.assertRaises(IndexError):
            self.make_queue().pop()

    def test_pop_until(self):
        elements = list("abcdeghijk")
        prioq = self.make_queue(elements)
        result = [ entry for entry, prio in prioq.pop_until(3) ]
        self.assertEqual(result, list("abcd"))
        self.assertEqual(len(prioq), len(elements) - len(result))

    def test_pop_until_none(self):
        elements = list("abcdeghijk")
        prioq = self.make_queue(elements)
        result = [ entry for entry, prio in prioq.pop_until(-1) ]
        self.assertEqual(result, [])
        self.assertEqual(len(prioq), len(elements) - len(result))

    def test_pop_until_overflow(self):
        elements = list("abcdeghijk")
        prioq = self.make_queue(elements)
        result = [ entry for entry, prio in prioq.pop_until(100) ]
        self.assertEqual(result, elements)
        self.assertEqual(len(prioq), len(elements) - len(result))
