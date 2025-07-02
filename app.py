from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import PyPDF2
import re
from flask import request, jsonify
from wtforms import StringField, IntegerField, SubmitField, TextAreaField, SelectField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Optional
import pdfplumber
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
DATABASE = 'EDMS.db'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Forms ---
class ProjectForm(FlaskForm):
    cust_no = StringField('Customer No', validators=[DataRequired()])
    customer_name = StringField('Customer Name', validators=[Optional()])
    additional_cust_no = StringField('Additional Customer No', validators=[Optional()])
    project_name = StringField('Project Name', validators=[DataRequired()])
    reference_no = StringField('Reference No', validators=[Optional()])
    project_status = SelectField(
        'Project Status',
        choices=[('Live', 'Live'), ('Hold', 'Hold'), ('Completed', 'Completed')],
        validators=[DataRequired()]
    )
    status_remarks = TextAreaField('Status Remarks', validators=[Optional()], render_kw={"rows": 2, "style": "resize:vertical;"})
    submit = SubmitField('Submit')

class CCOForm(FlaskForm):
    cust_no = StringField('Customer No', validators=[DataRequired()])
    comml_coordinator = StringField('Commercial Coordinator', validators=[Optional()])
    staff_no_cco = StringField('Staff No', validators=[Optional()])
    mobile_cco = StringField('Mobile', validators=[Optional()])
    auto_cco = StringField('Auto', validators=[Optional()])
    mail_cco = StringField('Email', validators=[Optional()])
    from_address = TextAreaField('From Address', validators=[Optional()], render_kw={"rows": 3, "style": "resize:vertical;"})
    submit = SubmitField('Submit')

class DelAddressForm(FlaskForm):
    cust_no = StringField('Customer No', validators=[DataRequired()])
    address_seq = IntegerField('Address Seq', validators=[DataRequired()])
    address = TextAreaField('Address', validators=[DataRequired()], render_kw={"rows": 4, "style": "resize:vertical;"})
    address_copies = StringField('No of Copies', validators=[Optional()])
    submit = SubmitField('Submit')

# --- Drawing Form ---
class DrawingForm(FlaskForm):
    drawing_ref = StringField('Drawing Ref', validators=[DataRequired()])
    sheet_no = StringField('Sheet No', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Submit')

#--- Routes ---
@app.route('/')
def index():
    db = get_db()
    projects = db.execute('SELECT * FROM projects').fetchall()
    updated_projects = []
    for project in projects:
        deladdrs = db.execute('SELECT address_copies FROM deladdress WHERE cust_no = ?', (project['cust_no'],)).fetchall()
        total_copies = 0
        for addr in deladdrs:
            try:
                copies = int(addr['address_copies']) if addr['address_copies'] else 0
            except ValueError:
                copies = 0
            total_copies += copies
        project_dict = dict(project)
        project_dict['total_copies'] = total_copies
        updated_projects.append(project_dict)
    return render_template('index.html', projects=updated_projects)

# --- Projects CRUD ---
@app.route('/project/add', methods=['GET', 'POST'])
def add_project():
    form = ProjectForm()
    if form.validate_on_submit():
        db = get_db()
        try:
            db.execute(
                'INSERT INTO projects (cust_no, customer_name, additional_cust_no, project_name, reference_no, project_status, status_remarks) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (form.cust_no.data, form.customer_name.data, form.additional_cust_no.data, form.project_name.data, form.reference_no.data, form.project_status.data, form.status_remarks.data)  
            )
            db.commit()
            flash('Project added successfully!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Customer No already exists!', 'danger')
    return render_template('project_form.html', form=form, action='Add')

@app.route('/project/edit/<cust_no>', methods=['GET', 'POST'])
def edit_project(cust_no):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE cust_no = ?', (cust_no,)).fetchone()
    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('index'))
    form = ProjectForm(data=project)
    if form.validate_on_submit():
        db.execute(
            'UPDATE projects SET customer_name=?, additional_cust_no=?, project_name=?, reference_no=?, project_status=?, status_remarks=? WHERE cust_no=?',
            (form.customer_name.data, form.additional_cust_no.data, form.project_name.data, form.reference_no.data, form.project_status.data, form.status_remarks.data, cust_no)
        )
        db.commit()
        flash('Project updated!', 'success')
        return redirect(url_for('index'))
    return render_template('project_form.html', form=form, action='Edit')

@app.route('/project/delete/<cust_no>', methods=['POST'])
def delete_project(cust_no):
    db = get_db()
    db.execute('DELETE FROM projects WHERE cust_no=?', (cust_no,))
    db.commit()
    flash('Project deleted.', 'info')
    return redirect(url_for('index'))

# --- CCO CRUD ---
@app.route('/cco')
def list_cco():
    db = get_db()
    ccos = db.execute('SELECT rowid, * FROM cco').fetchall()
    return render_template('cco_list.html', ccos=ccos)

@app.route('/cco/add', methods=['GET', 'POST'])
def add_cco():
    form = CCOForm()
    if form.validate_on_submit():
        db = get_db()
        db.execute(
            'INSERT INTO cco (cust_no, comml_coordinator, staff_no_cco, mobile_cco, auto_cco, mail_cco, from_address) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (form.cust_no.data, form.comml_coordinator.data, form.staff_no_cco.data, form.mobile_cco.data, form.auto_cco.data, form.mail_cco.data, form.from_address.data)
        )
        db.commit()
        flash('CCO added.', 'success')
        return redirect(url_for('list_cco'))
    return render_template('cco_form.html', form=form, action='Add')

@app.route('/cco/edit/<int:rowid>', methods=['GET', 'POST'])
def edit_cco(rowid):
    db = get_db()
    cco = db.execute('SELECT rowid, * FROM cco WHERE rowid = ?', (rowid,)).fetchone()
    if not cco:
        flash('CCO not found.', 'danger')
        return redirect(url_for('list_cco'))
    form = CCOForm(data=cco)
    if form.validate_on_submit():
        db.execute(
            'UPDATE cco SET cust_no=?, comml_coordinator=?, staff_no_cco=?, mobile_cco=?, auto_cco=?, mail_cco=?, from_address=? WHERE rowid=?',
            (form.cust_no.data, form.comml_coordinator.data, form.staff_no_cco.data, form.mobile_cco.data, form.auto_cco.data, form.mail_cco.data, form.from_address.data, rowid)
        )
        db.commit()
        flash('CCO updated!', 'success')
        return redirect(url_for('list_cco'))
    return render_template('cco_form.html', form=form, action='Edit')

@app.route('/cco/delete/<int:rowid>', methods=['POST'])
def delete_cco(rowid):
    db = get_db()
    db.execute('DELETE FROM cco WHERE rowid=?', (rowid,))
    db.commit()
    flash('CCO deleted.', 'info')
    return redirect(url_for('list_cco'))

# --- DelAddress CRUD ---
@app.route('/deladdress')
def list_deladdress():
    db = get_db()
    deladdrs = db.execute('SELECT * FROM deladdress').fetchall()
    return render_template('deladdress_list.html', deladdrs=deladdrs)

@app.route('/deladdress/add', methods=['GET', 'POST'])
def add_deladdress():
    form = DelAddressForm()
    if form.validate_on_submit():
        db = get_db()
        db.execute(
            'INSERT INTO deladdress (cust_no, address_seq, address, address_copies) VALUES (?, ?, ?, ?)',
            (form.cust_no.data, form.address_seq.data, form.address.data, form.address_copies.data)
        )
        db.commit()
        flash('Delivery address added.', 'success')
        return redirect(url_for('list_deladdress'))
    return render_template('deladdress_form.html', form=form, action='Add')

@app.route('/deladdress/edit/<int:id>', methods=['GET', 'POST'])
def edit_deladdress(id):
    db = get_db()
    deladdr = db.execute('SELECT * FROM deladdress WHERE id = ?', (id,)).fetchone()
    if not deladdr:
        flash('Address not found.', 'danger')
        return redirect(url_for('list_deladdress'))
    form = DelAddressForm(data=deladdr)
    if form.validate_on_submit():
        db.execute(
            'UPDATE deladdress SET cust_no=?, address_seq=?, address=?, address_copies=? WHERE id=?',
            (form.cust_no.data, form.address_seq.data, form.address.data, form.address_copies.data, id)
        )
        db.commit()
        flash('Delivery address updated!', 'success')
        return redirect(url_for('list_deladdress'))
    return render_template('deladdress_form.html', form=form, action='Edit')

@app.route('/deladdress/delete/<int:id>', methods=['POST'])
def delete_deladdress(id):
    db = get_db()
    db.execute('DELETE FROM deladdress WHERE id=?', (id,))
    db.commit()
    flash('Delivery address deleted.', 'info')
    return redirect(url_for('list_deladdress'))

@app.route('/elsts', methods=['GET', 'POST'])
def elsts():
    db = get_db()
    if request.method == 'POST':
        cust_no = request.form['cust_no']
        elst_no = request.form['elst_no']
        project_name = request.form['project_name']
        description = request.form['description']
        pdf = request.files['pdf_filename']
        filename = None
        if pdf:
            filename = secure_filename(pdf.filename)
            pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("""
            INSERT INTO erection_lists (cust_no, elst_no, project_name, pdf_filename, description, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cust_no, elst_no, project_name, filename, description, uploaded_at))
        db.commit()
        flash('ELST added successfully!', 'success')
        return redirect(url_for('elsts'))

    cust_no_filter = request.args.get('cust_no', '')
    if cust_no_filter:
        elsts = db.execute("SELECT * FROM erection_lists WHERE cust_no=? ORDER BY elst_no", (cust_no_filter,)).fetchall()
    else:
        elsts = db.execute("SELECT * FROM erection_lists ORDER BY cust_no, elst_no").fetchall()
    customers = db.execute("SELECT cust_no, project_name FROM projects ORDER BY project_name").fetchall()
    return render_template('elsts.html', elsts=elsts, customers=customers)

# --- Drawing Management for ELSTs ---

@app.route('/elst/<int:erection_list_id>/drawings')
def elst_drawings(erection_list_id):
    db = get_db()
    elst = db.execute('SELECT * FROM erection_lists WHERE id=?', (erection_list_id,)).fetchone()
    drawings = db.execute('SELECT * FROM elst_drawings WHERE erection_list_id=?', (erection_list_id,)).fetchall()
    return render_template('elst_drawings.html', elst=elst, drawings=drawings)

@app.route('/elst/<int:erection_list_id>/drawings/add', methods=['GET', 'POST'])
def add_drawing(erection_list_id):
    form = DrawingForm()
    if form.validate_on_submit():
        db = get_db()
        db.execute(
            'INSERT INTO elst_drawings (erection_list_id, drawing_ref, sheet_no, description) VALUES (?, ?, ?, ?)',
            (erection_list_id, form.drawing_ref.data, form.sheet_no.data, form.description.data)
        )
        db.commit()
        flash('Drawing added!', 'success')
        return redirect(url_for('elst_drawings', erection_list_id=erection_list_id))
    return render_template('drawing_form.html', form=form, action='Add', erection_list_id=erection_list_id)

@app.route('/elst/<int:erection_list_id>/drawings/edit/<int:drawing_id>', methods=['GET', 'POST'])
def edit_drawing(erection_list_id, drawing_id):
    db = get_db()
    drawing = db.execute('SELECT * FROM elst_drawings WHERE id=?', (drawing_id,)).fetchone()
    form = DrawingForm(data=drawing)
    if form.validate_on_submit():
        db.execute(
            'UPDATE elst_drawings SET drawing_ref=?, sheet_no=?, description=? WHERE id=?',
            (form.drawing_ref.data, form.sheet_no.data, form.description.data, drawing_id)
        )
        db.commit()
        flash('Drawing updated!', 'success')
        return redirect(url_for('elst_drawings', erection_list_id=erection_list_id))
    return render_template('drawing_form.html', form=form, action='Edit', erection_list_id=erection_list_id)

@app.route('/elst/<int:erection_list_id>/drawings/delete/<int:drawing_id>', methods=['POST'])
def delete_drawing(erection_list_id, drawing_id):
    db = get_db()
    db.execute('DELETE FROM elst_drawings WHERE id=?', (drawing_id,))
    db.commit()
    flash('Drawing deleted.', 'info')
    return redirect(url_for('elst_drawings', erection_list_id=erection_list_id))

@app.route('/extract_elst_data', methods=['POST'])
def extract_elst_data():
    file = request.files.get('pdf')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    try:
        file_bytes = file.read()
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages[:2]:
            text += page.extract_text() or ""
        match = re.search(r'ELST\s*No\.?\s*:?[\s\-]*(\d+)', text, re.IGNORECASE)
        elst_no = match.group(1) if match else ""

        drawings = []
        table_data = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages[:2]):
                tables = page.extract_tables()
                for table in tables:
                    headers = [cell.strip().lower() if cell else "" for cell in table[0]]
                    if any("drawing" in h for h in headers) and any("title" in h for h in headers):
                        for row in table[1:]:
                            drawing = {}
                            for idx, cell in enumerate(row):
                                drawing[headers[idx]] = cell
                            drawings.append(drawing)
                        table_data = table
        result = {
            'elst_no': elst_no,
            'message': "ELST No extracted." if elst_no else "ELST No not found in PDF.",
            'extracted_text': text,
            'table_data': table_data,
            'drawings': drawings
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)