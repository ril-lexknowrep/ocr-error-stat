import json
from sys import path
from more_itertools import split_into

CLM_PATH = '/storage/sata2tbssd/character_language_models/'
path.append(CLM_PATH)

import lstm_model
from encode_characters import InputEncoder, OutputEncoder

input_enc = InputEncoder(file=CLM_PATH+"input_encoder.json")
output_enc = OutputEncoder(file=CLM_PATH+"output_encoder.json")

bilstm_model = lstm_model.BiLSTM_Model.load(
    CLM_PATH + 'bilstm_model_512.h5', input_enc, output_enc)

diff_fname = 'fr15output_FR15_FR16_diffs.json'

with open(diff_fname) as json_file:
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

preds = bilstm_model.predict_subsequences(
    sequences, start_indices=None, end_indices=None,
    token_dicts=False, batch_size=1024)

print(len(preds))
assert len(preds) == len(sequences)

perplexities = [pred['substr-perpl'] for pred in preds]

# for perpl, text, start, end in zip(perplexities, sequences,
#                                    start_indices, end_indices):
#     print(perpl, text[start:end])

split_preds = split_into(perplexities, split_counts)
split_sources = split_into(sources, split_counts)

outfile = open(diff_fname[:-len('.json')] + "_eval.txt", 'w', encoding='utf-8')

for line_context, line_diffs, line_prs, line_srcs in zip(
                                contexts, diffs, split_preds, split_sources):
    best_pred = min(line_prs)
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
        print('\t'.join([f"›{diff['a']}‹", f"›{diff['b']}‹",
                         f'›{diff[winner]}‹',
                         f'{min_a:.4f}', f'{min_b:.4f}', line_context]),
              file=outfile)

# print(len(split_counts))
# print(len(sequences))

# from more_itertools import split_into

# split_texts = split_into(sequences, split_counts)

# for split in split_texts:
#     for line in split:
#         print(line)
#     print()
