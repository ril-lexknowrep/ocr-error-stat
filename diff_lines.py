import json
from sys import argv
from align.align_lines import list_lines
import networkx as nx
import difflib

LR_CONTEXT = 30  # left/right context required by the LM to decide on a target sequence

# characters to be evaluated to the left of the first diff
# and to the right of the last diff as part of the target sequence
TARGET_CONTEXT = 5 
MAX_DIFFS_PER_LINE = 6

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
        else:
            seg_string += f'[{seg["a"]}/{seg["b"]}]'
    return(seg_string)


def remove_hyphen(text, r_context):
    if len(text) > 2 and text[-1] == '-' and text [-2] != ' ':
        if ((text.endswith('sz-')
            and any(t.startswith('sz') for t in r_context))
            or
            (text.endswith('zs-')
            and any(t.startswith('zs') for t in r_context))
            or
            (text.endswith('cs-')
            and any(t.startswith('cs') for t in r_context))
            or
            (text[-2] == 'y'
            and
            (text.endswith('gy-')
            and any(t.startswith('gy') for t in r_context))
            or
            (text.endswith('ny-')
            and any(t.startswith('ny') for t in r_context))
            or
            (text.endswith('ty-')
            and any(t.startswith('ty') for t in r_context))
            or
            (text.endswith('ly-')
            and any(t.startswith('ly') for t in r_context)))
        ):
            return text[:-2], 2
        elif text[-2].isupper() or text[-2].isnumeric():
            return text, 0
        else:
            return text[:-1], 1
    else:
        return text + ' ', -1


def clean_str(s):
    return s.strip().replace('\xad', '-')

def main():
    print(argv[1])
    with open(argv[1]) as alignment_file:
        alignment = json.load(alignment_file)

    with open(alignment['a_file']) as a_file:
        a_data = json.load(a_file)

    with open(alignment['b_file']) as b_file:
        b_data = json.load(b_file)

    diff_dict = {
        'alignment_file': argv[1],
        'a_label': 'FR14',
        'b_label': 'FR15',
        # 'a_label': alignment['a_label'],
        # 'b_label': alignment['b_label'],
        'alt_sets': []}

    for page_num, page in enumerate(alignment['pages']):
#        print("page", page_num)
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
            num_diffs = sum(1 for seg in segs if seg.tag != 'equal')
            if num_diffs > MAX_DIFFS_PER_LINE:
                continue

            graph, node_text, node_source = diffs_to_graph(segs)
            path_texts, path_sources = graph_paths(graph, node_text, node_source)
#            print(num_diffs, len(path_texts), get_diff_string(segs))

            diff_list = [{'a': seg["a"], 'b': seg['b']}
                            for seg in segs
                            if seg.tag != 'equal']

            diff_dict['alt_sets'].append(
                {'a_text': a_text, 'b_text': b_text, 'diffs': diff_list,
                 'context': '', 'alternatives': []})

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

            # add previous line for additional left context if necessary
            l_missing = TARGET_CONTEXT + LR_CONTEXT - diff_start

            a_prev_text = ''
            if a_prev_line >= 0:
                a_prev_text = clean_str(a_page[a_prev_line]['text'])

            b_prev_text = ''
            if b_prev_line >= 0:
                b_prev_text = clean_str(b_page[b_prev_line]['text'])

            a_next_text = ''
            if a_next_line < len(a_page):
                a_next_text = clean_str(a_page[a_next_line]['text'])

            b_next_text = ''
            if b_next_line < len(b_page):
                b_next_text = clean_str(b_page[b_next_line]['text'])

            if l_missing <= 0:
                l_context = ['']
            elif a_prev_text == b_prev_text and a_next_text == b_next_text:
                l_context = [a_prev_text]
            else:
                l_context = [a_prev_text, b_prev_text]
            
            for ix, prev_line in enumerate(l_context):
                if len(prev_line) > 2 and prev_line[-1] == '-' and prev_line [-2] != ' ':
                    if ((prev_line.endswith('sz-')
                        and (a_text.startswith('sz') or b_text.startswith('sz')))
                        or
                        (prev_line.endswith('zs-')
                        and (a_text.startswith('zs') or b_text.startswith('zs')))
                        or
                        (prev_line.endswith('cs-')
                        and (a_text.startswith('cs') or b_text.startswith('cs')))
                        or
                        (prev_line[-2] == 'y'
                        and
                        (prev_line.endswith('gy-')
                        and (a_text.startswith('gy') or b_text.startswith('gy')))
                        or
                        (prev_line.endswith('ny-')
                        and (a_text.startswith('ny') or b_text.startswith('ny')))
                        or
                        (prev_line.endswith('ty-')
                        and (a_text.startswith('ty') or b_text.startswith('ty')))
                        or
                        (prev_line.endswith('ly-')
                        and (a_text.startswith('ly') or b_text.startswith('ly'))))
                    ):
                        l_context[ix] = prev_line[:-2]
                    elif prev_line[-2].isupper() or prev_line[-2].isnumeric():
                        l_context[ix] = prev_line
                    else:
                        l_context[ix] = prev_line[:-1]
                else:
                    l_context[ix] = prev_line + ' '

            eval_start = []
            for prev_line in l_context:
                eval_start.append(max(0, diff_start + len(prev_line) - TARGET_CONTEXT))

            # add next line for additional right context if necessary
            r_missing = TARGET_CONTEXT + LR_CONTEXT - diff_end

            if r_missing <= 0:
                r_context = ['']
            elif a_prev_text == b_prev_text and a_next_text == b_next_text:
                r_context = [a_next_text]
            else:
                r_context = [a_next_text, b_next_text]
            
            # check whether a_text and b_text end in a hyphen

            _, a_removed = remove_hyphen(a_text, r_context)
            _, b_removed = remove_hyphen(b_text, r_context)

            # generate alternatives

            diff_dict['alt_sets'][-1]['context'] =\
                ' // '.join([l_context[0], get_diff_string(segs), r_context[0]])

            for text_variant, sources in zip(path_texts, path_sources):
                for lc, rc, start in zip(l_context, r_context, eval_start):
                    if a_removed >= 0 and sources[-1] == 'a':
                        if a_removed:
                            center = text_variant[:-a_removed]
                        else:
                            center = text_variant
                        end = max(0, diff_end - TARGET_CONTEXT + len(rc) - a_removed)
                    elif b_removed >= 0 and sources[-1] == 'b':
                        if b_removed:
                            center = text_variant[:-b_removed]
                        else:
                            center = text_variant
                        end = max(0, diff_end - TARGET_CONTEXT + len(rc) - b_removed)
                    else:
                        center = text_variant + ' '
                        end = max(0, diff_end - TARGET_CONTEXT + len(rc) + 1)
                    concat_text = lc + center + rc
                    conc_end = len(concat_text) - end
                    # print('CENT', center)
                    # print('LC:', lc)
                    # print('RC:', rc)
                    # print('CC:', concat_text)
                    eval_span = concat_text[:start] + '##' + concat_text[start:conc_end] + '##' + concat_text[conc_end:]
#                    print(eval_span)
#                    print(f"{sources}, {start}, {conc_end}")

                    diff_dict['alt_sets'][-1]['alternatives'].append(
                        {'text': concat_text, 'sources': sources,
                         'start': start, 'end': conc_end})

    with open(argv[1][:-len('.json')] + '_diffs.json', 'w', encoding='utf-8') as diff_file:
        json.dump(diff_dict, diff_file)

if __name__ == '__main__':
    main()
