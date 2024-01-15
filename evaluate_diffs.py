import json
import os
from pathlib import Path
from sys import path, argv
from more_itertools import split_into

CLM_PATH = '/storage/sata2tbssd/character_language_models/'
path.append(CLM_PATH)

import lstm_model
from encode_characters import InputEncoder, OutputEncoder

MAX_DIFFS_PER_DOC = 30000

input_enc = InputEncoder(file=CLM_PATH+"input_encoder.json")
output_enc = OutputEncoder(file=CLM_PATH+"output_encoder.json")

bilstm_model = lstm_model.BiLSTM_Model.load(
    CLM_PATH + 'bilstm_model_512.h5', input_enc, output_enc)

diff_dir = argv[1]
diff_files = os.listdir(diff_dir)

for diff_fname in diff_files:
    print(diff_fname)
    if not diff_fname.endswith('_diffs.json'):
        continue

    if Path(diff_dir + '/' + diff_fname[:-len('.json')] + '_eval.json').exists():
        continue

    with open(diff_dir + '/' + diff_fname) as json_file:
        diff_dict = json.load(json_file)

    a_label = diff_dict['a_label']
    b_label = diff_dict['b_label']

    diffs = []
    contexts = []

    sequences = []
    sources = []
    split_counts = []

    start_indices = []
    end_indices = []

    for alt_set in diff_dict['alt_sets']:
        split_counts.append(len(alt_set['alternatives']))
        diffs.append(alt_set['diffs'])
        contexts.append(alt_set['context'])
        for alt in alt_set['alternatives']:
            sequences.append(alt['text'])
            sources.append(alt['sources'])
            start_indices.append(alt['start'])
            end_indices.append(alt['end'])

    assert len(sequences) == len(sources)
    assert len(sequences) == len(start_indices)
    assert len(sequences) == len(end_indices)
    print(len(sequences))

    if len(sequences) == 0 or len(sequences) > MAX_DIFFS_PER_DOC:
        continue

    preds = bilstm_model.predict_subsequences(
        sequences, start_indices=None, end_indices=None,
        token_dicts=False, batch_size=12000)

#    print(len(preds))
    assert len(preds) == len(sequences)

    perplexities = [pred['substr-perpl'] for pred in preds]

    # for perpl, text, start, end in zip(perplexities, sequences,
    #                                    start_indices, end_indices):
    #     print(perpl, text[start:end])

    split_preds = split_into(perplexities, split_counts)
    split_sources = split_into(sources, split_counts)

    outfile = open(diff_dir + '/' + diff_fname[:-len('.json')] + "_eval.tsv",
                   'w', encoding='utf-8')
    out_dict = {'diff_file': diff_fname, "a_label": a_label,
                "b_label": b_label, "alt_sets": []}

    for line_context, line_diffs, line_prs, line_srcs in zip(
                                contexts, diffs, split_preds, split_sources):
        best_pred = min(line_prs)
        out_dict['alt_sets'].append({'diffs': line_diffs, 'winners': [],
                                    'min_perplexities': []})
        print('', file=outfile)
        for ix, diff in enumerate(line_diffs):
            a_preds = [p for p, s in zip(line_prs, line_srcs) if s[ix] == 'a']
            b_preds = [p for p, s in zip(line_prs, line_srcs) if s[ix] == 'b']
            min_a = min(a_preds)
            min_b = min(b_preds)
            if min_a < min_b:
                winner = 'a'
            else:
                winner = 'b'
            out_dict['alt_sets'][-1]['winners'].append(winner)
            out_dict['alt_sets'][-1]['min_perplexities'].append(
                {'a': f'{min_a:.4f}', 'b': f'{min_b:.4f}'})

            print('\t'.join([f"›{diff['a']}‹", f"›{diff['b']}‹",
                             f'›{diff[winner]}‹',
                             f'{min_a:.4f}', f'{min_b:.4f}', line_context]),
                  file=outfile)
        assert len(out_dict['alt_sets'][-1]['diffs']) ==\
            len(out_dict['alt_sets'][-1]['winners'])
    outfile.close()

    with open(diff_dir + '/' + diff_fname[:-len('.json')] + '_eval.json',
              'w') as out_json:
        json.dump(out_dict, out_json)
