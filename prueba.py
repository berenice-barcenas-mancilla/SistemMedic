from flask import Flask, render_template, request, Response, send_file
from flask_mysqldb import MySQL
from PyPDF2 import PdfReader, PdfWriter
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__, static_folder='static')
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'medsys'
app.secret_key = 'mysecretkey'
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('consulta.html')

@app.route('/consulta')
def consulta():
    return render_template('consulta.html')

@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM diagnosticos WHERE id=5')
    data = cur.fetchall()
    cur.close()

    pdf_filename = generar_reporte_pdf(data)

    return send_file(pdf_filename, as_attachment=True)

def generar_reporte_pdf(data):
    template_path = "static/template.pdf"
    pdf_filename = "receta_medica.pdf"
    
    packet = io.BytesIO()
    # Create a new PDF with reportlab
    c = canvas.Canvas(packet, pagesize=letter)
    
    c.drawString(30, 750, 'RECETA MÉDICA')
    c.drawString(30, 735, 'CLÍNICA SAN JUAN')
    c.drawString(500, 750, "Fecha: 13/08/2023")
    c.line(480, 747, 580, 747)

    c.drawString(30, 725, 'PACIENTE:')
    c.drawString(120, 725, "Nombre del Paciente")
    c.line(120, 723, 380, 723)

    c.drawString(30, 703, 'MEDICAMENTOS:')
    y_position = 683
    for row in data:
        id_value = row[0]
        medicamento = row[1]
        dosis = row[2]
        frecuencia = row[3]
        c.drawString(30, y_position, f"ID: {id_value}")
        c.drawString(30, y_position - 20, f"Medicamento: {medicamento}")
        c.drawString(30, y_position - 40, f"Dosis: {dosis}")
        c.drawString(30, y_position - 60, f"Frecuencia: {frecuencia}")
        y_position -= 80
    
    c.save()
    
    # Move to the beginning of the packet
    packet.seek(0)
    
    # Create a PyPDF2 reader object from the existing template PDF
    existing_pdf = PdfReader(template_path)
    
    # Create a new PDF writer
    pdf_writer = PdfWriter()
    
    # Add the content from the packet to the new PDF
    new_pdf = PdfReader(packet)
    pdf_writer.add_page(existing_pdf.pages[0])
    pdf_writer.pages[0].merge_page(new_pdf.pages[0])
    
    # Save the result to the output PDF
    with open(pdf_filename, "wb") as output_pdf:
        pdf_writer.write(output_pdf)
    
    return pdf_filename

if __name__ == '__main__':
    app.run(port=5000, debug=True)
