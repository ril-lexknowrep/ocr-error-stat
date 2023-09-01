from sys import argv
import json
import numpy as np
from scipy.spatial.distance import cdist
import time

from Levenshtein import distance

MAXDIST = 30
IDX_MULT = 1000

def list_lines(data):
    line_list = []
    for block in data["blocks"]:
        for line in block["lines"]:
            line_list.append(line)
    return line_list


def main():
    start_t = time.time()
    with (open(argv[1]) as a_file,
        open(argv[2]) as b_file):
        doc_a = json.load(a_file)
        doc_b = json.load(b_file)

    for p_num in range(min(len(doc_a['pages']), len(doc_b['pages']))):
        print("Page", p_num)
        a_list = list_lines(doc_a['pages'][p_num])
        b_list = list_lines(doc_b['pages'][p_num])

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
        pairs_list = []

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

        print()

        for line_a in range(len(a_list)):
            pairs_list.append((line_a, pairs_dict.get(line_a)))

        paired_bs = set(pairs_dict.values())
        for line_b in range(len(b_list)):
            if line_b not in paired_bs:
                pairs_list.append((None, line_b))

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
