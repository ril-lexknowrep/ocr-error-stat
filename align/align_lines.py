from sys import argv
import json
import numpy as np
from scipy.spatial.distance import cdist
import time

from Levenshtein import distance

MAXDIST = 30
IDX_MULT = 1000
HEADER_HEIGHT = 0.1
FOOTER_HEIGHT = 0.1


def list_lines(data, skip_header=True, doc=''):
    if skip_header:
        page_height = data['cropbox'][3] - data['cropbox'][1]
        header_bottom = page_height * HEADER_HEIGHT + data['cropbox'][1]
        footer_top = page_height * (1 - FOOTER_HEIGHT) + data['cropbox'][1]
        line_list = []
        top_block_height = page_height
        bottom_block_height = 0
        for block in data["blocks"]:
            if (len(block['lines']) == 1
                    and block['bbox'][3] < header_bottom
                    and block['bbox'][3] < top_block_height):
                top_block_height = block['bbox'][3]
            elif (len(block['lines']) == 1
                    and block['bbox'][1] > footer_top
                    and block['bbox'][1] > bottom_block_height):
                bottom_block_height = block['bbox'][1]
        if top_block_height == page_height:
            top_block_height = 0
        if bottom_block_height == 0:
            bottom_block_height = page_height

    for block in data["blocks"]:
        if (skip_header
                and len(block['lines']) == 1
                and block['bbox'][1] < top_block_height):
            print(f"Skipping header {doc}: {block['lines'][0]['text']}")
            continue
        elif (skip_header
                and len(block['lines']) == 1
                and block['bbox'][3] > bottom_block_height):
            print(f"Skipping footer {doc}: {block['lines'][0]['text']}")
            continue

        for line in block["lines"]:
            line_list.append(line)
    return line_list


def same_row(line_a, line_b):
    # base line of line_a is within the vertical span of line_b,
    # and vice versa
    # return (line_a['bbox'][1] < line_b['bbox'][3]
    #         and line_a['bbox'][3] > line_b['bbox'][1])
    return (line_a['origin'][1] > line_b['bbox'][1]
            and line_a['origin'][1] < line_b['bbox'][3]
            and line_b['origin'][1] > line_a['bbox'][1]
            and line_b['origin'][1] < line_a['bbox'][3])


def align_1_2(unpaired_this, unpaired_other,
              this_list, other_list,
              this_name, other_name):
    '''
    Check unpaired lines for possible 1:2 alignments
    '''

    concats = []
    new_pairs = []
    unpaired_this_sorted = sorted(unpaired_this,
                                    key=lambda x: this_list[x]['bbox'][0])
    for i in range(len(unpaired_this) - 1):
        for j in range(i + 1, len(unpaired_this)):
            if same_row(this_list[unpaired_this_sorted[i]],
                        this_list[unpaired_this_sorted[j]]):
                concats.append((unpaired_this_sorted[i],
                                unpaired_this_sorted[j]))

    if concats and unpaired_other:
        print("Concats")
        print(concats)
        # create an array containing the centers of the concatenated lines
        concat_centers = np.array(
            [((this_list[conc[0]]['center'][0]
               + this_list[conc[1]]['center'][0]) / 2,
              (this_list[conc[0]]['center'][1]
               + this_list[conc[1]]['center'][1]) / 2)
                for conc in concats])
        other_centers = np.array([other_list[line_nr]['center']
                                  for line_nr in unpaired_other])

        unp_distance_matrix = cdist(concat_centers, other_centers)
        unp_idx_matrix = np.zeros([len(concat_centers), len(other_centers)],
                                    dtype=int)
        for i in range(len(concat_centers)):
            for j in range(len(other_centers)):
                unp_idx_matrix[i, j] = IDX_MULT * i + j

        for i, a in enumerate(concat_centers):
            for j, b in enumerate(other_centers):
                if unp_distance_matrix[i, j] < MAXDIST:
                    unp_distance_matrix[i, j] += distance(a, b)
                else:
                    unp_distance_matrix[i, j] = np.inf

        while unp_distance_matrix.shape[0] > 0 and unp_distance_matrix.shape[1] > 0:
            min_i, min_j = np.unravel_index(np.argmin(unp_distance_matrix),
                                            unp_distance_matrix.shape)
            if unp_distance_matrix[min_i, min_j] == np.inf:
                break
            else:
                concat_idx = unp_idx_matrix[min_i, min_j] // IDX_MULT
                unpaired_other_idx = unp_idx_matrix[min_i, min_j] % IDX_MULT
                concat_1 = this_list[concats[concat_idx][0]]
                concat_2 = this_list[concats[concat_idx][1]]
                print(f'{this_name}1', concats[concat_idx][0], concat_1['text'])
                print(f'{this_name}2', concats[concat_idx][1], concat_2['text'])
                print(other_name, unpaired_other[unpaired_other_idx],
                      other_list[unpaired_other[unpaired_other_idx]]['text'])

                # Change text and coordinates of the left half of the
                # concatenated line and remove text from the right half
                concat_1['bbox'] = [
                    concat_1['bbox'][0],
                    min(concat_1['bbox'][1], concat_2['bbox'][1]),
                    concat_2['bbox'][2],
                    max(concat_1['bbox'][3], concat_2['bbox'][3])]
                concat_1['text'] += concat_2['text']
                concat_1['center'] = [
                    (concat_1['bbox'][0] + concat_1['bbox'][2]) / 2,
                    (concat_1['bbox'][1] + concat_1['bbox'][3]) / 2]
                
                concat_2['text'] = ' '

                new_pairs.append((concats[concat_idx][0],
                                  unpaired_other[unpaired_other_idx]))

                unp_distance_matrix = np.delete(
                    np.delete(unp_distance_matrix, min_i, axis=0), min_j, axis=1)
                unp_idx_matrix = np.delete(
                    np.delete(unp_idx_matrix, min_i, axis=0), min_j, axis=1)

    return new_pairs


def find_unpaired(a_list, b_list, pairs_dict):
    paired_bs = set(pairs_dict.values())
    unpaired_a = [i for i in range(len(a_list))
                  if i not in pairs_dict]
    unpaired_b = [i for i in range(len(b_list))
                  if i not in paired_bs]
    return unpaired_a, unpaired_b


def main():
    start_t = time.time()
    with (open(argv[1]) as a_file,
        open(argv[2]) as b_file):
        doc_a = json.load(a_file)
        doc_b = json.load(b_file)

    for p_num in range(min(len(doc_a['pages']), len(doc_b['pages']))):
        print("Page", p_num)
        a_list = list_lines(doc_a['pages'][p_num], doc='A')
        b_list = list_lines(doc_b['pages'][p_num], doc='B')

        a_no_space = [a['text'].replace(' ', '')
                      for a in a_list]
        b_no_space = [b['text'].replace(' ', '')
                      for b in b_list]

        a_centers = np.array([line['center'] for line in a_list])
        b_centers = np.array([line['center'] for line in b_list])

        # Calculate the Euclidean distance matrix
        try:
            distance_matrix = cdist(a_centers, b_centers)
        except ValueError:
            distance_matrix = np.zeros([0, 0])
        idx_matrix = np.zeros([len(a_centers), len(b_centers)], dtype=int)
        for i in range(len(a_centers)):
            for j in range(len(b_centers)):
                idx_matrix[i, j] = IDX_MULT * i + j
        pairs_dict = {}

        for i, a in enumerate(a_no_space):
            for j, b in enumerate(b_no_space):
                if distance_matrix[i, j] < MAXDIST:
                    # Levenshtein distance between line texts, ignoring spaces
                    distance_matrix[i, j] += distance(a, b)
                else:
                    distance_matrix[i, j] = np.inf

        while distance_matrix.shape[0] > 0 and distance_matrix.shape[1] > 0:
            min_i, min_j = np.unravel_index(np.argmin(distance_matrix),
                                            distance_matrix.shape)
            if distance_matrix[min_i, min_j] == np.inf:
                break
            else:
                line_a = idx_matrix[min_i, min_j] // IDX_MULT
                line_b = idx_matrix[min_i, min_j] % IDX_MULT
                pairs_dict[line_a] = line_b
                print(line_a, line_b, distance_matrix[min_i, min_j])
                distance_matrix = np.delete(
                    np.delete(distance_matrix, min_i, axis=0), min_j, axis=1)
                idx_matrix = np.delete(
                    np.delete(idx_matrix, min_i, axis=0), min_j, axis=1)

        unpaired_a, unpaired_b = find_unpaired(a_list, b_list, pairs_dict)

        new_pairs = align_1_2(unpaired_a, unpaired_b, a_list, b_list,
                              'A', 'B')

        for a, b in new_pairs:
            pairs_dict[a] = b

        unpaired_a, unpaired_b = find_unpaired(a_list, b_list, pairs_dict)

        new_pairs = align_1_2(unpaired_b, unpaired_a, b_list, a_list,
                              'B', 'A')
        for b, a in new_pairs:
            pairs_dict[a] = b

        pairs_list = []
        for a, b in pairs_dict.items():
            pairs_list.append((a, b))

        unpaired_a, unpaired_b = find_unpaired(a_list, b_list, pairs_dict)

        for a in unpaired_a:
            pairs_list.append((a, None))
        for b in unpaired_b:
            pairs_list.append((None, b))

        pairs_list = sorted(pairs_list, key=lambda x: (x[0] or 0) or (x[1] or 0))
        print()

        for line_a, line_b in pairs_list:
            try:
                a_text = a_list[line_a]['text'].rstrip().replace("\u00AD", "-")
            except:
                a_text = None
            try:
                b_text = b_list[line_b]['text'].rstrip().replace("\u00AD", "-")
            except:
                b_text = None
            print(line_a, a_text)
            if a_text == b_text:
                print("=")
                print(line_b)
            else:
                print("!!!")
                print(line_b, b_text)
            print()
    print("Time", time.time() - start_t)

if __name__ == '__main__':
    main()
