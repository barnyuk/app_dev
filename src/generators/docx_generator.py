"""DOCX protocol generation."""

import logging

import docx
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt
from docx.text.paragraph import Paragraph
import os
from copy import deepcopy
from config.settings import SITPLANES_DIR, OUTPUT_DIR, template_foldet_path, prev_prot_path


logger = logging.getLogger(__name__)

KEY_WORK_TABLE = '{{ТАБЛИЦА}}'
KEY_FINAL_TABLE = '{{ЧИСТОВАЯТАБЛИЦА}}'
KEY_PLAN = '{{СИТПЛАН}}'
KEY_PROTOCOL = '{{НП}}'
SPECIAL_KEYS = (KEY_WORK_TABLE, KEY_FINAL_TABLE, KEY_PLAN)

WORK_OUTPUT_DIR = OUTPUT_DIR / 'work'
FINAL_OUTPUT_DIR = OUTPUT_DIR / 'final_protocol'
INDOR_AZIMUTHES = ['0', '360']
MAKE_WORK_PROTOCOLS, MAKE_FINAL_PROTOCOLS = True, True
objects_list = []


def get_params(work_par, word_par):
    global MAKE_WORK_PROTOCOLS, MAKE_FINAL_PROTOCOLS 
    MAKE_WORK_PROTOCOLS, MAKE_FINAL_PROTOCOLS = work_par, word_par


def generate_protocols(obj, sitplan_dir=None, output_dir=None) -> None:
    """Generate both work and final protocol documents for a base station."""
    work_template = template_foldet_path / 'work_temp.docx'
    word_template = template_foldet_path / f'{obj.operator}.docx'

    standards = ', '.join(obj.standarts)
    permissions = '\n'.join(
        f'{k}: {", ".join(map(str, v))}' for k, v in obj.permissions.items()
    )

    # Use provided sitplan_dir or fall back to the configured default
    if sitplan_dir is None:
        sitplan_dir = SITPLANES_DIR
    sitplan_path = str(sitplan_dir / f'{obj.operator}_{obj.bsn_id}.png')

    data_to_fill = {
        '{{ЗАЯВИТЕЛЬ}}': obj.operator_address,
        KEY_PROTOCOL: obj.protocol_number,
        '{{НОМЕРБС}}': obj.bsn_id,
        '{{АДРЕСБС}}': obj.bsn_address,
        KEY_WORK_TABLE: work_table,
        KEY_FINAL_TABLE: make_final_table,
        '{{ПРЕДСТАВИТЕЛЬ}}': obj.operator_worker,
        '{{ДАТАВОРД}}': obj.word_date,
        '{{ЧАСТОТЬ}}': obj.show_frequences(),
        '{{ДАТА}}': obj.date,
        # ВНИМАНИЕ: в этом ключе первая буква — латинская "C", а не кириллическая "С"!
        '{{СТАНДАРТЫ}}':obj.show_standarts(),
        '{{C}}': f'Стандарты: {standards}\nразрешения: {permissions}',
        KEY_PLAN: sitplan_path,
    }

    # Use provided output_dir or fall back to the configured default
    if output_dir is None:
        work_dir = WORK_OUTPUT_DIR
        final_dir = FINAL_OUTPUT_DIR
    else:
        work_dir = output_dir / 'work'
        final_dir = output_dir / 'final_protocol'

    if MAKE_WORK_PROTOCOLS:
        _render_document(obj, data_to_fill, work_template, work_dir, work=True)
    if MAKE_FINAL_PROTOCOLS:
        _render_document(
        obj, data_to_fill, word_template, final_dir,
        col_widths=[Cm(5), Cm(2.5), Cm(2.75), Cm(2.5), Cm(1.7), Cm(2.73)],
        table_index=2,
        )
        objects_list.append(obj) 

def find_prev_data(bsn_id: str) -> docx.Document.table:
    for protocol in os.listdir(prev_prot_path):

        if bsn_id in protocol:
            table = docx.Document(prev_prot_path / protocol).tables[-1]

            return deepcopy(table._tbl)

        


def _render_document(obj, data, template, output_folder,
                     col_widths=None, table_index=None, work=False) -> None:
    """Render a protocol document: substitute data, tables and site plan."""
    document = docx.Document(str(template))
    simple_keys = {k: v for k, v in data.items() if k not in SPECIAL_KEYS}

    for paragraph in document.paragraphs:
        text = paragraph.text
        if not any(k in text for k in data):
            continue  

        if KEY_PLAN in text:
            _insert_picture(paragraph, data[KEY_PLAN])

        for key in (KEY_WORK_TABLE, KEY_FINAL_TABLE):
            if key in text:
                data[key](document, obj, paragraph)

        for k, v in simple_keys.items():
            if k in text:
                _replace_in_paragraph(paragraph, k, str(v))

    _replace_in_header_footers(document, simple_keys)

    if col_widths is not None and table_index is not None:
        table = document.tables[table_index]
        table.autofit = False
        for row in table.rows:
            for idx, w in enumerate(col_widths):
                row.cells[idx].width = w

    if work:
        try:
            document._body._element.append(find_prev_data(obj.bsn_id))
        except Exception:
            logger.warning('Не удалось вставить таблицу (%s)',obj.bsn_id)


    output_folder.mkdir(parents=True, exist_ok=True)
    document.save(output_folder / f'05-{obj.protocol_number}_{data["{{НОМЕРБС}}"]}_{obj.operator}.docx')




def _replace_in_paragraph(paragraph, key, value) -> None:
    """Replace a placeholder even if Word split it across multiple runs."""
    if not paragraph.runs:
        return
    full_text = ''.join(run.text for run in paragraph.runs)
    if key not in full_text:
        return
    paragraph.runs[0].text = full_text.replace(key, value)
    for run in paragraph.runs[1:]:
        run.text = ''


def _insert_picture(paragraph, image_path) -> None:
    """Insert an image in place of the placeholder (inside the paragraph)."""
    try:
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        run.text = ''
        run.add_picture(image_path, width=Inches(6))
    except Exception as e:
        logger.warning('Не удалось вставить ситуационный план (%s): %s', image_path, e)
        _replace_in_paragraph(paragraph, KEY_PLAN, '')


def _replace_simple_keys_in_paragraphs(paragraphs, simple_keys) -> None:
    """Replace simple placeholders across a collection of paragraphs."""
    for paragraph in paragraphs:
        text = paragraph.text
        if not any(k in text for k in simple_keys):
            continue
        for k, v in simple_keys.items():
            if k in text:
                _replace_in_paragraph(paragraph, k, str(v))


def _iter_all_paragraphs(container):
    """Return every w:p inside a header/footer wrapped as Paragraph.

    python-docx's ``container.paragraphs`` returns only ``w:p`` elements that
    are direct children of the header/footer. Paragraphs placed inside
    ``w:sdt`` content controls (e.g. Word page-number fields) or table cells
    are missed in that way. ``iter()`` walks the whole XML subtree, so those
    paragraphs are found and processed as well.
    """
    return [
        Paragraph(p, container)
        for p in container._element.iter(qn('w:p'))
    ]


def _replace_in_header_footers(document, simple_keys) -> None:
    """Replace simple placeholders (e.g. {{НП}}) in all headers and footers.

    Processes default, first-page and even-page headers/footers, including
    paragraphs inside ``w:sdt`` content controls and header tables.
    """
    hf_attrs = (
        'header', 'first_page_header', 'even_page_header',
        'footer', 'first_page_footer', 'even_page_footer',
    )
    for section in document.sections:
        for attr in hf_attrs:
            header_or_footer = getattr(section, attr)
            try:
                if header_or_footer.is_linked_to_previous:
                    continue
            except Exception:
                pass
            _replace_simple_keys_in_paragraphs(
                _iter_all_paragraphs(header_or_footer), simple_keys)


def set_table_borders(table) -> None:
    """Add outer and inner borders to a table."""
    tbl_pr = table._tbl.tblPr

    existing = tbl_pr.find(qn('w:tblBorders'))
    if existing is not None:
        tbl_pr.remove(existing)

    tbl_borders = OxmlElement('w:tblBorders')
    for name in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border = OxmlElement(f'w:{name}')
        border.set(qn('w:val'), 'single')    # одиночная линия
        border.set(qn('w:sz'), '4')          # толщина 0.5 pt
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')  # черный
        tbl_borders.append(border)

    tbl_pr.append(tbl_borders)


def insert_table(table, paragraph) -> None:
    """Move a ready table to the placeholder paragraph position."""
    paragraph._p.addprevious(table._tbl)
    paragraph.text = ''


def _fill_table(table, matrix, col_widths=None, center_cols=(), font_size=10) -> None:
    """Single pass: widths, text, alignment, font."""
    for row, row_data in zip(table.rows, matrix):
        for col_idx, text in enumerate(row_data):
            cell = row.cells[col_idx]
            if col_widths:
                cell.width = col_widths[col_idx]
            cell.text = text
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                if col_idx in center_cols:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.size = Pt(font_size)
                    run.font.name = 'Times New Roman'


def work_table(doc, obj, paragraph) -> None:
    freqs = obj.frequences
    placeholder = '              /              /              '

    header = [
        '№п/п',
        'Наименование места\nизмерений\n(географические\nкоординаты)',
        'Ориентировочное\nрасстояние, м',
        'Частота,\nМГц\n(диапазон\nчастот)',
        'Измеряемая величина,\nразмерность\n(Напряжённость\nэлектромагнитного поля, дБмкВ (ППЭ, мкВт/см ²))'
    ]

    table_matrix = [header]
    if len(obj.azimuthes) == 1 and set(obj.azimuthes).issubset(set(INDOR_AZIMUTHES)):
        row_count = 11
        for t_index in range(1, row_count):
                    block = [['', '', '', str(freq), placeholder] for freq in freqs]
                    block[0][0] = str(t_index)
                    block[0][1] = f'A{t_index}'
                    table_matrix.extend(block)
        
    elif 3600 in freqs:
        data = [
    ['1', 'Т1', ' ','1800', placeholder],
    ['2', 'Т2', ' ','1800', placeholder],
    ['', '', ' ','2600', placeholder],
    ['', '', ' ','3500', placeholder],
    ['3', 'Т3', ' ','1800', placeholder],
    ['4', 'Т4', ' ','1800', placeholder],
    ['5', 'Т5', ' ','1800', placeholder],
    ['', '', ' ','2600', placeholder],
    ['', '', ' ','3600', placeholder],
    ['6', 'Т6', ' ','1800', placeholder],
    ['7', 'Т7', ' ','1800', placeholder],
    ['8', 'Т8', ' ','1800', placeholder],
    ['', '', ' ','2600', placeholder],
    ['', '', ' ','3600', placeholder],
    ['9', 'Т9', ' ','1800', placeholder],
    ['10', 'Т10', ' ','1800', placeholder],
    ['', '', '','2600', placeholder],
    ['', '', '','3600', placeholder]
]
        for dt in data:
            table_matrix.append(dt)            
    else:
        row_count = len(obj.azimuthes) + (3 if obj.city_minsk else 2)
        for t_index in range(1, row_count):
            block = [['', '', '', str(freq), placeholder] for freq in freqs]
            block[0][0] = str(t_index)
            block[0][1] = f'Т{t_index}'
            table_matrix.extend(block)

    table = doc.add_table(rows=len(table_matrix), cols=5)
    set_table_borders(table)
    _fill_table(
        table, table_matrix,
        col_widths=[Cm(1.5), Cm(4.5), Cm(3.5), Cm(2.3), Cm(5.8)],
        center_cols=(3,),
    )
    insert_table(table, paragraph)


def make_final_table(doc, obj, paragraph) -> None:
    header = ['Описание точек\nизмерения уровней ЭМП',
              'Ориентиро-\nвочное\nрасстояние, м',
              'Высота от\nопорной\nповерхности, м',
              'Частота\n(диапазон\nчастот), МГц',
              'ПДУ\nмкВт/\nсм2',
              'Измеряемая\nвеличина\nППЭ,\nмкВт/см2']

    under_header = ['1', '2', '3', '4', '5', '6']

    table_matrix = [header, under_header]
    if len(obj.azimuthes) == 1 and set(obj.azimuthes).issubset(set(INDOR_AZIMUTHES)):
        row_count = 10
        for i in range(row_count):
            table_matrix.append([
                f'Возле А',
                '',
                '2',
                '/\n'.join(map(str, obj.frequences)),
                '10',
                '/\n'.join('±' for _ in obj.frequences),
            ])
    elif 3600 in obj.frequences:
        data = [
            ['Точка 1 территория,\nприлегающая к антеннам','','2','10','1800','±'],
            ['Точка 2 территория,прилегающая к антеннам','','2','10',
             '/\n'.join(map(str, obj.frequences)),'/\n'.join('±' for _ in obj.frequences)],
            ['Точка 3 территория,\nприлегающая к антеннам','','2','10','1800','±'],
            ['Точка 4 территория,\nприлегающая к антеннам','', '2','10','1800','±'],
            ['Точка 5 территория,\nприлегающая к антеннам','', '2','10',
                         '/\n'.join(map(str, obj.frequences)),'/\n'.join('±' for _ in obj.frequences)],
            ['Точка 6 территория,\nприлегающая к антеннам','', '2','10','1800','±'],
            ['Точка 7 территория,\nприлегающая к антеннам','', '2','10','1800','±'],
            ['Точка 8 территория,\nприлегающая к антеннам','', '2','10',
                                     '/\n'.join(map(str, obj.frequences)),'/\n'.join('±' for _ in obj.frequences)],
            ['Точка 9 территория,\nприлегающая к антеннам','', '2','10','1800','±'],
            ['Точка 10 внутри здания,\n','','1,7/1,0/0,5','',
                                                 '/\n'.join(map(str, obj.frequences)),'/\n'.join('±' for _ in obj.frequences)],
        ]
        for dt in data:
            table_matrix.append(dt)

    else:
        outdoor_points = len(obj.azimuthes)
        total_points = outdoor_points + (2 if obj.city_minsk else 1)
        for i in range(total_points):
            table_matrix.append([
                f'Точка {i + 1} внутри здания,' if i==total_points-1 and obj.city_minsk
                else f'Точка {i + 1} территория,\nприлегающая к антеннам',
                '',
                '1,7/1,0/0,5' if i==total_points-1 and obj.city_minsk else '2',
                '/\n'.join(map(str, obj.frequences)),
                '10',
                '/\n'.join('±' for _ in obj.frequences),
            ])
        

    table = doc.add_table(rows=len(table_matrix), cols=6)
    set_table_borders(table)
    _fill_table(table, table_matrix, center_cols=(1, 2, 3, 4, 5))
    insert_table(table, paragraph)
