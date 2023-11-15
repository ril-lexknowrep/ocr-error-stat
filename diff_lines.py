import json
from sys import argv
from align.align_lines import list_lines
import networkx as nx
import difflib


class DiffSegment:
    '''A class that provides a comfortable interface for difflib diffs.'''

    def __init__(self, tag: str,
                 a_start: int, a_end: int,
                 b_start: int, b_end: int,
                 a_text: str, b_text: str):
        self.tag = tag
        self.a_start = a_start
        self.a_end = a_end
        self.b_start = b_start
        self.b_end = b_end
        self.alternatives = {'a': a_text[a_start:a_end],
                             'b': b_text[b_start:b_end]}
        self._extended_alternatives = None

    def __getitem__(self, item):
        if item == '_':
            return self.alternatives['b']
        elif (self._extended_alternatives is not None
              and item in self._extended_alternatives):
            return self._extended_alternatives[item]
        else:
            return self.alternatives[item]

    def __getattr__(self, attr):
        if attr in self.alternatives:
            return self.alternatives[attr]
        else:
            raise AttributeError()

    def __str__(self):
        msg = f'\n{self.tag}'

        if self.tag == 'equal':
            msg += (f'\n{self.a_start}..{self.a_end} / '
                    + f'{self.b_start}..{self.b_end} = {self.a}')
        else:  # replace, insert, delete
            msg += (f'\n{self.a_start}..{self.a_end} = {{{self.a}}}'
                    + f'\n{self.b_start}..{self.b_end} = {{{self.b}}}')

        return msg


def diffs_to_graph(segs, a_label='a', b_label='b'):
    graph = nx.DiGraph()
    node_text = {}
    node_source = {}
    graph.add_node(0)
    current_node = 0
    for seg in segs:
        if seg.tag == 'equal':
            next_node = current_node + 1
            graph.add_node(next_node)
            node_text[next_node] = seg['a']
            graph.add_edge(current_node, next_node)
            current_node = next_node
        elif seg.tag == 'replace':
            a_node = current_node + 1
            b_node = current_node + 2
            join_node = current_node + 3
            graph.add_node(a_node)
            graph.add_node(b_node)
            graph.add_node(join_node, text='')
            node_text[a_node] = seg['a']
            node_text[b_node] = seg['b']
            node_source[a_node] = a_label
            node_source[b_node] = b_label
            graph.add_edge(current_node, a_node)
            graph.add_edge(current_node, b_node)
            graph.add_edge(a_node, join_node)
            graph.add_edge(b_node, join_node)
            current_node = join_node
        elif seg.tag == 'insert':
            a_node = current_node + 1
            b_node = current_node + 2
            join_node = current_node + 3
            graph.add_node(a_node)
            graph.add_node(b_node)
            graph.add_node(join_node)
            node_text[b_node] = seg['b']
            node_source[a_node] = a_label
            node_source[b_node] = b_label
            graph.add_edge(current_node, a_node)
            graph.add_edge(current_node, b_node)
            graph.add_edge(a_node, join_node)
            graph.add_edge(b_node, join_node)
            current_node = join_node
        elif seg.tag == 'delete':
            a_node = current_node + 1
            b_node = current_node + 2
            join_node = current_node + 3
            graph.add_node(a_node)
            graph.add_node(b_node)
            graph.add_node(join_node)
            node_text[a_node] = seg['a']
            node_source[a_node] = a_label
            node_source[b_node] = b_label
            graph.add_edge(current_node, a_node)
            graph.add_edge(current_node, b_node)
            graph.add_edge(a_node, join_node)
            graph.add_edge(b_node, join_node)
            current_node = join_node
    return graph, node_text, node_source


def graph_paths(graph, node_text, node_source):
    path_texts = []
    path_sources = []
    for path in list(nx.all_simple_paths(graph, source=0, target=list(graph.nodes)[-1])):
        path_texts.append(''.join([node_text.get(e, '') for e in path]))
        path_sources.append(''.join([node_source.get(e, '') for e in path]))
    return path_texts, path_sources


def get_diff_string(segs):
    seg_string = ''
    for seg in segs:
        if seg.tag == 'equal':
            seg_string += seg['a']
        elif seg.tag == 'replace':
            seg_string += f'[{seg["a"]}/{seg["b"]}]'
        elif seg.tag == 'insert':
            seg_string += f'[/{seg["b"]}]'
        elif seg.tag == 'delete':
            seg_string += f'[{seg["a"]}/]'
    return(seg_string)


def clean_str(s):
    return s.strip().replace('\xad', '-')

def main():
    with open(argv[1]) as alignment_file:
        alignment = json.load(alignment_file)

    with open(alignment['a_file']) as a_file:
        a_data = json.load(a_file)

    with open(alignment['b_file']) as b_file:
        b_data = json.load(b_file)

    for page_num, page in enumerate(alignment['pages']):
        print("page", page_num)
        a_page = list_lines(a_data['pages'][page_num], verbose=False)
        b_page = list_lines(b_data['pages'][page_num], verbose=False)

        for k, v in page.items():
            if k == 'null' or v is None:
                continue
            if '+' in k:
                a_lines = k.split('+')
                a_lines = [int(a_lines[0]), int(a_lines[1])]
                a_text = clean_str(a_page[a_lines[0]]['text'] + a_page[a_lines[1]]['text'])
                a_prev_line = a_lines[0] - 1
                a_next_line = a_lines[1] + 1
            else:
                a_text = clean_str(a_page[int(k)]['text'])
                a_prev_line = int(k) - 1
                a_next_line = int(k) + 1
            if type(v) == str and '+' in v:
                b_lines = v.split('+')
                b_lines = [int(b_lines[0]), int(b_lines[1])]
                b_text = clean_str(b_page[b_lines[0]]['text'] + b_page[b_lines[1]]['text'])
                b_prev_line = b_lines[0] - 1
                b_next_line = b_lines[1] + 1
            else:
                b_text = clean_str(b_page[int(v)]['text'])
                b_prev_line = int(v) - 1
                b_next_line = int(v) + 1

            if a_text == b_text:
                continue

            matcher = difflib.SequenceMatcher(autojunk=False)
            matcher.set_seqs(a_text, b_text)
            opcodes = matcher.get_opcodes()
            segs = [DiffSegment(*opcode, a_text, b_text) for opcode in opcodes]
            graph, node_text, node_source = diffs_to_graph(segs)
            path_texts, path_sources = graph_paths(graph, node_text, node_source)
            print(len(path_texts), get_diff_string(segs))

            ROOT_NODE = 0
            # if root branches immediately
            if len(graph[ROOT_NODE]) == 2:
                diff_start = 0
            else:
                diff_start = len(node_text[1])
            
            final_node = list(graph.nodes)[-1]

            # if final node has two parents
            if len(list(graph.predecessors(final_node))) == 2:
                diff_end = 0   # counting from the end
            else:
                diff_end = len(node_text[final_node])

if __name__ == '__main__':
    main()
