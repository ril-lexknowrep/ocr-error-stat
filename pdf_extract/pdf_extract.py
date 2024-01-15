import json
from sys import argv
import fitz

PDF_FLAGS = (fitz.TEXT_PRESERVE_WHITESPACE
             | fitz.TEXT_INHIBIT_SPACES
             | fitz.TEXT_MEDIABOX_CLIP)


def restructure_pdf(page_pdf):
    output_dict = {}
    page_dict = page_pdf.get_text("dict", flags=PDF_FLAGS)
    # The cropbox is a Rect object which can't be serialised by json
    output_dict['cropbox'] = to_tuple(page_pdf.cropbox)
    output_dict['blocks'] = []
    for block in page_dict["blocks"]:
        output_dict['blocks'].append(
            {'number': block['number'],
             'lines': [],
             'bbox': block['bbox']})
        current_block = output_dict['blocks'][-1]
        lines = block["lines"]
        for line in lines:
            spans = line['spans']
            line_text = ''.join(span['text'] for span in spans)
            if (current_block['lines']
                and spans[0]['origin'][1]
                    == current_block['lines'][-1]['origin'][1]):
                # If line is horizontally to the right of the previous line
                # of this block, merge with previous line
                new_bbox = list(current_block['lines'][-1]['bbox'])
                new_bbox[2] = line['bbox'][2]
                new_bbox[1] = min(new_bbox[1], line['bbox'][1])
                new_bbox[3] = max(new_bbox[3], line['bbox'][3])
                current_block['lines'][-1]['bbox'] = new_bbox
                current_block['lines'][-1]['text'] += line_text
                current_block['lines'][-1]['center'] = (
                    (new_bbox[0] + new_bbox[2]) / 2,
                    (new_bbox[1] + new_bbox[3]) / 2)
            else:
                current_block['lines'].append(
                    {'origin': spans[0]['origin'],
                    'bbox': line['bbox'],
                    'text': line_text,
                    'center': (
                        (line['bbox'][0] + line['bbox'][2]) / 2,   # x
                        (line['bbox'][1] + line['bbox'][3]) / 2)   # y
                })
    return output_dict


def to_tuple(rect):
    return (rect.x0, rect.y0, rect.x1, rect.y1)


def process_pdf():
    try:
        pdf_path, output_path = argv[1], argv[2]
    except IndexError:
        pdf_path, output_path = argv[1], None
    output_data = {'pages': []}
    pdf_document = fitz.open(pdf_path)

    for page in pdf_document:
        output_data['pages'].append(
            restructure_pdf(page))

    if output_path is None:
        print(json.dumps(output_data))
    else:
        with open(output_path, 'w') as json_out:
            json.dump(output_data, json_out)


def main():
    process_pdf()


if __name__ == '__main__':
    main()
