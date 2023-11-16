import json
CLM_PATH = '/storage/sata2tbssd/character_language_models/'
path.append(CLM_PATH)

import lstm_model
from encode_characters import InputEncoder, OutputEncoder

input_enc = InputEncoder(file=CLM_PATH+"input_encoder.json")
output_enc = OutputEncoder(file=CLM_PATH+"output_encoder.json")

bilstm_model = lstm_model.BiLSTM_Model.load(
    CLM_PATH + 'bilstm_model_512.h5', input_enc, output_enc)

with open('fr15output_FR15_FR16_diffs.json') as json_file:
    diff_dict = json.load(json_file)

a_label = diff_dict['a_label']
b_label = diff_dict['b_label']

sequences = []
sources = []
split_counts = []

start_indices = []
end_indices = []

for alt_set in diff_dict['alt_sets']:
    split_counts.append(len(alt_set['alternatives']))
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

for perpl, text, start, end in zip(perplexities, sequences, start_indices, end_indices):
    print(perpl, text[start:end])

# print(len(split_counts))
# print(len(sequences))

# from more_itertools import split_into

# split_texts = split_into(sequences, split_counts)

# for split in split_texts:
#     for line in split:
#         print(line)
#     print()
