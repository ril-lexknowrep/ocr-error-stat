import json
import zipfile
import numpy as np
import xycut
import reading_order

PAGE_DIGITS = 4

def restructure_json(json_data):
    parsed_json = json.loads(json_data)
    output_dict = {}
    page_height = parsed_json["cropbox"][-1]
    output_dict['cropbox'] = parsed_json["cropbox"]
    output_dict['blocks'] = []
    for block in parsed_json["blocks"]:
        output_dict['blocks'].append(
            {'number': len(output_dict['blocks']),
             'lines': []})
        current_block = output_dict['blocks'][-1]
        lines = block["lines"]
        for line in lines:
            spans = line['spans']
            origin = (spans[0]['x'],                   # x
                      page_height - spans[0]['line'])  # y
            right_edge = origin[0] + sum(spans[-1]['w'])
            max_asc, max_desc = spans[0]['asc'], spans[0]['desc']
            line_text = ''.join(spans[0]['s'])
            for span in spans[1:]:
                if span['asc'] > max_asc:
                    max_asc = span['asc']
                if span['desc'] < max_desc:   # desc is negative!
                    max_desc = span['desc']
                line_text += ''.join(span['s'])
            current_block['lines'].append(
                {'origin': origin,
                 'bbox': (
                    origin[0],              # left
                    origin[1] - max_asc,    # top
                    right_edge,             # right
                    origin[1] - max_desc),  # bottom (desc is negative!)
                 'text': line_text,
                 'center': (
                    (origin[0] + right_edge) / 2,            # x
                    origin[1] - (max_desc + max_asc) / 2)    # y
                 })
        current_block['bbox'] = (
            min(line['bbox'][0] for line in current_block['lines']),  # left
            current_block['lines'][0]['bbox'][1],                     # top
            max(line['bbox'][2] for line in current_block['lines']),  # right
            current_block['lines'][-1]['bbox'][3]                     # bottom
        )
    return output_dict

def process_cbz(cbz_path, output_path):
    output_data = {'pages': []}
    with (zipfile.ZipFile(cbz_path, 'r') as cbz_zip,
            open(output_path, 'w') as json_out):
        json_files = [file for file in cbz_zip.namelist() if file.endswith(".json")]

        for json_file_path in json_files:
            json_data = cbz_zip.read(json_file_path).decode('utf-8')
            output_data['pages'].append(restructure_json(json_data))

        json.dump(output_data, json_out)

process_cbz('2000Folyoirat_2000folyoirat_1989_04.cbz', "output.json")
