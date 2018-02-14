import os
import shutil
import os.path as op
import pdfkit
import argparse
from src.utils import utils
from src.utils import args_utils as au


def read_html(html_fname):
    with open(html_fname, 'r') as html_file:
        html = html_file.read()
    return html


def replace_fields(html, patient_name, nmr_number, scan_date):
    html = html.replace('Patient name', patient_name)
    html = html.replace('MRN number', nmr_number)
    html = html.replace('Date', scan_date)
    return html


def create_new_html(html, html_fname):
    with open(html_fname, 'w') as html_file:
        html_file.write(html)


def create_pdf(html_fname, pdf_fname):
    pdfkit.from_file(html_fname, pdf_fname)


def main(html_template_fname, scan_fol, patient_name, mrn, scan_date, output_fname=''):
    if utils.get_parent_fol(html_template_fname) != scan_fol:
        shutil.copy(html_template_fname, scan_fol)
    if output_fname == '':
        output_fname = op.join(scan_fol, '{}.pdf'.format(mrn))
    new_html_fname =  utils.change_fname_extension(output_fname, 'html')
    html = read_html(html_template_fname)
    html = replace_fields(html, patient_name, mrn, scan_date)
    create_new_html(html, new_html_fname)
    create_pdf(new_html_fname, output_fname)
    os.remove(op.join(scan_fol, utils.namebase_with_ext(html_template_fname)))
    # os.remove(new_html_fname)


if __name__ == '__main__':
    template_fname = '/homes/5/npeled/space1/Documents/natalia/template_report.html'
    scan_fol = '/homes/5/npeled/space1/Documents/natalia/scan'

    parser = argparse.ArgumentParser(description='MMVT')
    parser.add_argument('--template_fol', required=True)
    parser.add_argument('--template_name', required=False, default='template_report.html')
    parser.add_argument('--scan_fol', required=True)
    parser.add_argument('--patient_name', required=True)
    parser.add_argument('--mrn', required=True)
    parser.add_argument('--scan_date', required=True)
    args = utils.Bag(au.parse_parser(parser))
    html_template_fname = op.join(args.template_fol, args.template_name)
    main(html_template_fname, args.scan_fol, args.patient_name, args.mrn, args.scan_date)


