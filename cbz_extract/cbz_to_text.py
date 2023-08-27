import json
import zipfile
import numpy as np
import xycut
import reading_order

PAGE_DIGITS = 4

def extract_json(json_data):
    # Parse the JSON data
    parsed_json = json.loads(json_data)

    # Extract and concatenate the text spans
    extracted_text = ""
    for block in parsed_json["blocks"]:
        extracted_text += "\n"
        for line in block["lines"]:
            for span in line["spans"]:
                extracted_text += "".join(span["s"])
            if extracted_text.endswith('-'):
                extracted_text += "\n"

    # Print the extracted text
    return extracted_text

def extract_naive(json_data):
    parsed_json = json.loads(json_data)
    extracted_text = ""

    # Flatten and sort blocks based on reading order
    blocks = []
    for block in parsed_json["blocks"]:
        lines = block["lines"]
        if lines:
            y_position = lines[-1]["spans"][0]["line"]
            x_position = lines[0]["spans"][0]["x"]
            blocks.append((x_position, y_position, block))
    blocks.sort(key=lambda b: (-b[1], -b[0]))  # Sort by y, then x

    # Extract text from sorted blocks
    for _, _, block in blocks:
        extracted_text += "\n"
        for line in block["lines"]:
            for span in line["spans"]:
                extracted_text += "".join(span["s"])
                
    return extracted_text

def extract_xycut(json_data):
    parsed_json = json.loads(json_data)
    page_height = parsed_json["cropbox"][-1]
    extracted_text = ""

    # Flatten and sort blocks based on reading order
    blocks = []
    for block in parsed_json["blocks"]:
        lines = block["lines"]
        if lines:
            first_line = lines[0]["spans"][0]
            last_line = lines[-1]["spans"][0]
            first_line_top = page_height - (first_line["line"] + first_line["asc"])
            last_line_bottom = page_height - (last_line["line"] + last_line["desc"])
            left_edge = min(line["spans"][0]["x"] for line in lines)
            right_edge = max(span["x"] + sum(span["w"]) for line in lines for span in line["spans"])
            blocks.append((left_edge, first_line_top, right_edge, last_line_bottom, block))

    # Extract text from sorted blocks

    boxes = np.array([block[:-1] for block in blocks])
    res = []
    print(boxes)
    if blocks:
        xycut.recursive_xy_cut(boxes.astype(int), np.arange(len(boxes)), res)
    print(res)
    assert len(res) == len(boxes)

    for idx in res:
        block = blocks[idx][-1]
        extracted_text += "\n"
        for line in block["lines"]:
            for span in line["spans"]:
                extracted_text += "".join(span["s"])
                
    return extracted_text

def extract_pdf_pig(json_data):
    parsed_json = json.loads(json_data)
    page_height = parsed_json["cropbox"][-1]
    extracted_text = ""
    order_detector = reading_order.UnsupervisedReadingOrderDetector()

    # Flatten and sort blocks based on reading order
    blocks = []
    for block in parsed_json["blocks"]:
        lines = block["lines"]
        if lines:
            first_line = lines[0]["spans"][0]
            last_line = lines[-1]["spans"][0]
            first_line_top = page_height - (first_line["line"] + first_line["asc"])
            last_line_bottom = page_height - (last_line["line"] + last_line["desc"])
            left_edge = min(line["spans"][0]["x"] for line in lines)
            right_edge = max(span["x"] + sum(span["w"]) for line in lines for span in line["spans"])
            blocks.append(
                reading_order.TextBlock(
                    block,
                    reading_order.BoundingBox(first_line_top,
                                              last_line_bottom,
                                              left_edge,
                                              right_edge),
                    len(blocks)))
    if blocks:
        for idx in order_detector.reorder(blocks):
            block = blocks[idx].data
            extracted_text += "\n"
            box = blocks[idx].BoundingBox
            extracted_text += f"B{idx}[{box.Top:.2f},{box.Bottom:.2f},{box.Left:.2f},{box.Right:.2f}]\n"
            for line in block["lines"]:
                for span in line["spans"]:
                    extracted_text += "".join(span["s"])
                extracted_text += "\n"

    return extracted_text

def process_cbz(cbz_path, output_path):
    with open(output_path, 'w', encoding='utf-8') as output_file:
        with zipfile.ZipFile(cbz_path, 'r') as cbz_zip:
            json_files = [file for file in cbz_zip.namelist() if file.endswith(".json")]

            for json_file_path in json_files:
                json_number = json_file_path[
                    -(PAGE_DIGITS + len('.json')):-len('.json')]
                json_data = cbz_zip.read(json_file_path).decode('utf-8')

                print("page", json_number)
                extracted_text = extract_pdf_pig(json_data)

                output_file.write(f"#{{page{json_number}}}\n")
                output_file.write(extracted_text + '\n\n')

# Replace these paths with your actual paths
cbz_file_path = "2000Folyoirat_2000folyoirat_1989_04.cbz"
output_file_path = "cbz_output.txt"

process_cbz(cbz_file_path, output_file_path)
