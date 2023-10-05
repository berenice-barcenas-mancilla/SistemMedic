#---------------------------------------Necesario para funcionar----------------------------------------------------------------------------

from flask import Flask,render_template,request,redirect,url_for,flash, after_this_request, send_file
from flask_mysqldb import MySQL
from PyPDF2 import PdfReader, PdfWriter
import io, bcrypt
from reportlab.lib.pagesizes import letter, landscape, A4, portrait
from reportlab.pdfgen import canvas
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin

app = Flask(__name__, static_folder='static')
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='medsys'
app.secret_key='mysecretkey'
mysql= MySQL(app)

login_manager = LoginManager(app)
login_manager.login_view = 'index'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.' 


class User(UserMixin):
    def __init__(self, id, rfc, pass_hash):
        self.id = id
        self.rfc = rfc
        self.pass_hash = pass_hash

    def get_id(self):
        return str(self.id)
    
    
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT id, rfc, pass FROM medicos WHERE id = %s', (user_id,))
    account = cur.fetchone()
    cur.close()

    if account:
        return User(id=account[0], rfc=account[1], pass_hash=account[2])
    return None

def encriptarContrasena(password):
    sal = bcrypt.gensalt()
    conHa = bcrypt.hashpw(password.encode(), sal)
    return conHa

RMED=0
IDMED=0

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/acceso-login', methods=["POST", "GET"])
def login():
    if request.method == 'POST' and 'txtRfc' in request.form and 'txtPassword' in request.form:
        _rfc = request.form['txtRfc']
        _password = request.form['txtPassword']

        cur = mysql.connection.cursor()
        cur.execute('SELECT id, rfc, pass FROM medicos WHERE rfc = %s', (_rfc,))
        account = cur.fetchone()

        if account and bcrypt.checkpw(_password.encode(), account[2].encode()):
            user = User(id=account[0], rfc=account[1], pass_hash=account[2])
            login_user(user)

            cur2 = mysql.connection.cursor()
            cur2.execute('SELECT rol_id FROM medicos INNER JOIN roles ON medicos.rol_id=roles.id WHERE medicos.id=%s', (account[0],))
            rol = cur2.fetchone()
            rolMedico = rol[0]
            
            global RMED
            global IDMED
            RMED=rol[0]
            IDMED=account[0]

            return redirect(url_for('dash', rolMedico=RMED, idMedico=IDMED))
        else:
            flash('Usuario o Contraseña Incorrectas')
            return render_template('login.html')
        
        

@app.route('/logout')
@login_required
def logout():
    @after_this_request
    def add_no_cache(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    logout_user()
    return redirect(url_for('index'))
########################################DASHBOARD#####################################################

########################################DASHBOARD#####################################################
@app.route('/dash')
@login_required
def dash():
    return render_template('dash.html', rolMedico=RMED, idMedico=IDMED)

###########################################   MEDICOS   #####################################################
@app.route('/addmedicos')
@login_required
def addmedicos():
    return render_template('addMedicos.html', rolMedico=RMED, idMedico=IDMED)

#Agregar un nuevo medico
@app.route('/addmedicosguardar', methods=['POST'])
def addmedicosguardar():
    if request.method == 'POST':
        # pasamos a variables el contenido de los input
        vnombre= request.form['txtnombre']
        vap= request.form['txtap']
        vam= request.form['txtam']
        vrfc=request.form['txtrfc']
        vcedula=request.form['txtcedula']
        vrol=request.form['txtrol']
        vpass=request.form['txtpass']
        conH=encriptarContrasena(vpass)
        
        # Conectar y ejecutar el insert
        CSGM = mysql.connection.cursor() # objeto de tipo cursor
        CSGM.execute('insert into medicos (nombre, ap, am, rfc, cedula, rol_id, pass) values (%s, %s, %s, %s, %s, %s, %s)',(vnombre, vap, vam, vrfc, vcedula, vrol, conH))
        mysql.connection.commit()
    flash('El medico fue agregado correctamente')
    return redirect(url_for('medicos'))


#Mostrar lista de Medicos
@app.route('/medicos')
@login_required
def medicos():
    SMCS = mysql.connection.cursor()
    if RMED==2:
        SMCS.execute("SELECT medicos.id, medicos.nombre, medicos.ap, medicos.am, medicos.rfc, medicos.cedula, roles.rol FROM `medicos` INNER JOIN roles on roles.id=medicos.rol_id")
    else:
        SMCS.execute('SELECT medicos.id, medicos.nombre, medicos.ap, medicos.am, medicos.rfc, medicos.cedula, roles.rol FROM medicos inner join roles on roles.id=medicos.rol_id where medicos.id=%s', (IDMED,))
    QueryMedicos = SMCS.fetchall()
    return render_template('showMedicos.html',listMedicos = QueryMedicos, rolMedico=RMED, idMedico=IDMED)


#Editar Medico
@app.route('/editMedico/<id>')
@login_required
def editMedico(id):
    EMCS = mysql.connection.cursor()
    EMCS.execute('select m.id, m.nombre, m.ap, m.am, m.rfc,m.cedula, r.rol, m.pass from medicos m inner join roles r on m.rol_id = r.id where m.id = %s',(id,))
    QueryEMId = EMCS.fetchone()
    q = mysql.connection.cursor()
    q.execute('select * from roles')
    Queryroles = q.fetchall()
    return render_template('editMedico.html',listEMId = QueryEMId, listRoles = Queryroles)


@app.route('/updateMedico/<id>', methods=['POST'])
def update(id):
    if request.method == 'POST':
        Vnombre = request.form['txtnombre']
        Vap = request.form['txtap']
        Vam = request.form['txtam']
        Vrfc = request.form['txtrfc']
        Vcedula = request.form['txtcedula']
        Vrol = request.form['txtrol']
        Vpass = request.form['txtpass']
        VpassOG = request.form['pass_original']

        if Vpass == VpassOG:
            conH = VpassOG
        else:
            conH = encriptarContrasena(Vpass)
            
        UpdMCur = mysql.connection.cursor()   
        UpdMCur.execute('UPDATE medicos SET nombre = %s, ap = %s, am = %s, rfc = %s, cedula = %s, rol_id  = %s, pass = %s WHERE id = %s', (Vnombre, Vap, Vam, Vrfc, Vcedula, Vrol, conH, id))
        mysql.connection.commit()
        flash('La información del Medico fue actualizada correctamente')

    return redirect(url_for('medicos'))

#Eliminar Medico
@app.route('/delMedico/<id>')
@login_required
def delMedico(id):
    DMCS = mysql.connection.cursor()
    DMCS.execute('SELECT * FROM medicos where id = %s',(id,))
    QueryId = DMCS.fetchone()
    
    return render_template('deleteMedico.html',listIdDlt = QueryId)

@app.route('/deleteMedico/<id>', methods=['POST'])
def delete(id):
    if request.method == 'POST':
        if request.form.get('action') == 'delete':
            DelCur = mysql.connection.cursor()
            DelCur.execute('delete from medicos where id = %s', (id,))
            mysql.connection.commit()
            flash('El Medico fue dado de baja correctamente')
        elif request.form.get('action') == 'cancel':
            flash('Eliminación cancelada')
    return redirect(url_for('medicos'))

###########################################   /MEDICOS   #####################################################

###########################################   DIAGNOSTICOS   #####################################################
@app.route('/addDiagnostico')
@login_required
def addDiagnostico():
    # Obtener lista de pacientes con nombre completo
    pacientes_cur = mysql.connection.cursor()
    if RMED==2:
        pacientes_cur.execute("SELECT id, CONCAT(nombre, ' ', ap, ' ', am) AS nombre_completo FROM pacientes")
    else:
        pacientes_cur.execute("SELECT id, CONCAT(nombre, ' ', ap, ' ', am) AS nombre_completo FROM pacientes where medico_id=%s", (IDMED,))
    lista_pacientes = pacientes_cur.fetchall()

    # Obtener lista de exploraciones para el paciente seleccionado
    
    exploraciones_cur = mysql.connection.cursor()
    exploraciones_cur.execute("SELECT id FROM exploraciones WHERE paciente_id = %s", (lista_pacientes[0][0],))  # Usamos el ID del primer paciente inicialmente
    lista_exploraciones = exploraciones_cur.fetchall()

    return render_template('addDiagnostico.html', pacientes=lista_pacientes, exploraciones=lista_exploraciones, rolMedico=RMED, idMedico=IDMED)

# Agregar un nuevo diagnóstico
@app.route('/guardarDiagnostico', methods=['POST'])
def guardarDiagnostico():
    if request.method == 'POST':
        # pasamos a variables el contenido de los input
        vpaciente = request.form['txtpaciente']
        vexpediente = request.form['txtexpediente']
        vsintomas = request.form['txtsintomas']
        vtratamiento = request.form['txttratamiento']
        vmedicamentos = request.form['txtmedicamentos']
        vindicaciones = request.form['txtindicaciones']
        CSGD = mysql.connection.cursor()  # objeto de tipo cursor
        CSGD.execute('INSERT INTO diagnosticos (paciente_id, expediente_id, sintomas, tratamiento, medicamentos, indicaciones) VALUES (%s, %s, %s, %s, %s, %s)', (vpaciente, vexpediente, vsintomas, vtratamiento, vmedicamentos, vindicaciones))
        mysql.connection.commit()
    flash('El diagnóstico fue agregado correctamente')
    return redirect(url_for('diagnosticos'))

# Mostrar lista de diagnósticos
@app.route('/diagnosticos')
@login_required
def diagnosticos():
    SDCS = mysql.connection.cursor()
    if RMED==2:
        SDCS.execute("SELECT diagnosticos.id, pacientes.nombre, pacientes.ap, pacientes.am, exploraciones.id, diagnosticos.sintomas, diagnosticos.tratamiento, diagnosticos.medicamentos, diagnosticos.indicaciones FROM pacientes inner join exploraciones on pacientes.id=exploraciones.paciente_id inner join diagnosticos on exploraciones.id=diagnosticos.expediente_id")
    else:
        SDCS.execute("SELECT diagnosticos.id, pacientes.nombre, pacientes.ap, pacientes.am, exploraciones.id, diagnosticos.sintomas, diagnosticos.tratamiento, diagnosticos.medicamentos, diagnosticos.indicaciones, medicos.id, medicos.nombre, medicos.ap, medicos.am FROM pacientes inner join exploraciones on pacientes.id=exploraciones.paciente_id inner join diagnosticos on exploraciones.id=diagnosticos.expediente_id inner join medicos on medicos.id=pacientes.medico_id where medicos.id=%s", (IDMED,))
    QueryDiagnostico = SDCS.fetchall()
    return render_template('showDiagnostico.html', listDiagnosticos=QueryDiagnostico, rolMedico=RMED, idMedico=IDMED)

# Editar diagnóstico
@app.route('/editDiagnostico/<id>')
@login_required
def editDiagnostico(id):
    EDCS = mysql.connection.cursor()
    EDCS.execute('SELECT * FROM diagnosticos WHERE id = %s', (id,))
    QueryEDId = EDCS.fetchone()
    return render_template('editDiagnostico.html', listEDId=QueryEDId, rolMedico=RMED, idMedico=IDMED)

@app.route('/updateDiagnostico/<id>', methods=['POST'])
def updateDiagnostico(id):
    if request.method == 'POST':

        Vsintomas = request.form['txtsintomas']
        Vtratamiento = request.form['txttratamiento']
        Vmedicamentos = request.form['txtmedicamentos']
        Vindicaciones = request.form['txtindicaciones']
        UpdDCur = mysql.connection.cursor()
        UpdDCur.execute('UPDATE diagnosticos SET sintomas = %s, tratamiento = %s, medicamentos = %s, indicaciones = %s WHERE id = %s', ( Vsintomas, Vtratamiento, Vmedicamentos, Vindicaciones, id))
        mysql.connection.commit()
    flash('La información del diagnóstico fue actualizada correctamente')
    return redirect(url_for('diagnosticos'))

# Eliminar diagnóstico
@app.route('/delDiagnostico/<id>')
@login_required
def delDiagnostico(id):
    DDCS = mysql.connection.cursor()
    DDCS.execute('SELECT * FROM diagnosticos WHERE id = %s', (id,))
    QueryId = DDCS.fetchone()
    return render_template('deleteDiagnostico.html', listIdDlt=QueryId)

@app.route('/deleteDiagnostico/<id>', methods=['POST'])
def deleteDiagnostico(id):
    if request.method == 'POST':
        if request.form.get('action') == 'delete':
            DelCur = mysql.connection.cursor()
            DelCur.execute('DELETE FROM diagnosticos WHERE id = %s', (id,))
            mysql.connection.commit()
            flash('El diagnóstico fue eliminado correctamente')
        elif request.form.get('action') == 'cancel':
            flash('Eliminación cancelada')
    return redirect(url_for('diagnosticos'))

###########################################   /DIAGNOSTICOS   #####################################################

###########################################   ESTUDIOS   #####################################################


@app.route('/borrarEstudio/<id>')
@login_required
def borrarEstudio(id):
    EDCS = mysql.connection.cursor()
    EDCS.execute('SELECT * FROM estudios inner join pacientes on pacientes.id=estudios.paciente_id WHERE estudios.id = %s', (id,))
    QueryEDId = EDCS.fetchone()

    CP = mysql.connection.cursor()
    CP.execute('SELECT * FROM pacientes where medico_id=%s', (IDMED,))
    NomPacientes=CP.fetchall()

    return render_template('deleteEstudio.html', rolMedico=RMED, idMedico=IDMED, estudio=QueryEDId, Nombres=NomPacientes)

@app.route('/deleteEstudio/<id>')
@login_required
def deleteEstudio(id):
    DelCur = mysql.connection.cursor()
    DelCur.execute('DELETE FROM estudios WHERE id = %s', (id,))
    mysql.connection.commit()
    flash('El diagnóstico fue eliminado correctamente')
    return redirect(url_for('estudios'))

@app.route('/editEstudio/<id>')
@login_required
def editEstudio(id):
    EDCS = mysql.connection.cursor()
    EDCS.execute('SELECT * FROM estudios inner join pacientes on pacientes.id=estudios.paciente_id WHERE estudios.id = %s', (id,))
    QueryEDId = EDCS.fetchone()

    CP = mysql.connection.cursor()
    CP.execute('SELECT * FROM pacientes where medico_id=%s', (IDMED,))
    NomPacientes=CP.fetchall()

    return render_template('editEstudio.html', rolMedico=RMED, idMedico=IDMED, estudio=QueryEDId, Nombres=NomPacientes)


@app.route('/updateEstudio/<id>', methods=['POST'])
@login_required
def updateEstudio(id):

    if request.method == 'POST':

        Vpaciente = request.form['txtpaciente']
        Vestudiomedico = request.form['txtEstudioMedico']
        Vdescripcion = request.form['txtDescripcion']
        UpdDCur = mysql.connection.cursor()
        UpdDCur.execute('UPDATE estudios SET paciente_id = %s, nombre = %s, descripcion = %s WHERE id = %s', ( Vpaciente, Vestudiomedico, Vdescripcion, id))
        mysql.connection.commit()
    flash('La información del estudio fue actualizada correctamente')

    return redirect(url_for('estudios'))

@app.route('/addEstudio')
@login_required
def addEstudio():
    # Obtener lista de pacientes con nombre completo
    pacientes_cur = mysql.connection.cursor()
    if RMED==2:
        pacientes_cur.execute("SELECT id, CONCAT(nombre, ' ', ap, ' ', am) AS nombre_completo FROM pacientes")
    else:
        pacientes_cur.execute("SELECT id, CONCAT(nombre, ' ', ap, ' ', am) AS nombre_completo FROM pacientes where medico_id=%s", (IDMED,))
    lista_pacientes = pacientes_cur.fetchall()
    return render_template('addEstudio.html', pacientes=lista_pacientes, rolMedico=RMED, idMedico=IDMED)

# Agregar un nuevo estudio medico
@app.route('/guardarEstudio', methods=['POST'])
def guardarEstudio():
    if request.method == 'POST':
        # pasamos a variables el contenido de los input
        vpaciente = request.form['txtpaciente']
        vnombre = request.form['txtnombre']
        vdescripcion = request.form['txtdescripcion']
        CSGE = mysql.connection.cursor()  # objeto de tipo cursor
        CSGE.execute('INSERT INTO estudios (paciente_id, nombre, descripcion) VALUES (%s, %s, %s)', (vpaciente,  vnombre, vdescripcion))
        mysql.connection.commit()
    flash('El estudio medico fue agregado correctamente')
    return redirect(url_for('estudios'))

# Mostrar lista de estudios medicos
@app.route('/estudios')
@login_required
def estudios():
    SECS = mysql.connection.cursor()
    SECS.execute("SELECT * FROM estudios inner join pacientes on estudios.paciente_id=pacientes.id")
    QueryEstudios = SECS.fetchall()
    return render_template('showEstudio.html', listEstudios=QueryEstudios, rolMedico=RMED, idMedico=IDMED)


###########################################   /ESTUDIOS   #####################################################

###########################################   PACIENTES   #####################################################
@app.route('/addPacientes')
@login_required
def addPacientes():
    # Obtener lista de medicos con nombre completo
    medicos_cur = mysql.connection.cursor()
    medicos_cur.execute("SELECT id, CONCAT(nombre, ' ', ap, ' ', am) AS nombre_completo FROM medicos")
    lista_medicos = medicos_cur.fetchall()
    
    # Obtener lista de enfermedades
    enfermedades_cur = mysql.connection.cursor()
    enfermedades_cur.execute("SELECT id,nombre FROM enfermedades")
    lista_enfermedades = enfermedades_cur.fetchall()
    
    return render_template('addPaciente.html', medicos=lista_medicos, enfermedades=lista_enfermedades, rolMedico=RMED, idMedico=IDMED)

# guardar nuevo paciente
@app.route('/guardarPaciente', methods=['POST', 'GET'])
def guardarPaciente():
    if request.method == 'POST':
        Vnombre = request.form['txtnombre']
        Vap = request.form['txtap']
        Vam = request.form['txtam']
        Vfechanacimiento = request.form['txtFechanacimiento']
        Valergias = request.form['txtalergias']
        Vantecedentes = request.form['txtantecedentes']
        Venfermedad = int(request.form['txtEnfermedades'])  # Asegúrate de que sea un entero / Ricardo: ????
        if RMED==1:
            Vmedico = IDMED
        else:
            Vmedico = int(request.form['txtmedico']) 
        CS = mysql.connection.cursor()
        CS.execute('INSERT INTO pacientes (nombre, ap, am, birthdate, alergias, antecedentes, enfermedad_id, medico_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (Vnombre, Vap, Vam, Vfechanacimiento, Valergias, Vantecedentes, Venfermedad, Vmedico))
        mysql.connection.commit()
        flash('El paciente fue agregado correctamente')
    return redirect(url_for('pacientes'))

# Mostrar lista de pacientes
@app.route('/pacientes')
@login_required
def pacientes():
    SPCS = mysql.connection.cursor()
    #SPCS.execute("SELECT * FROM pacientes")
    if RMED==1:
        SPCS.execute('SELECT pacientes.id, pacientes.nombre, pacientes.ap, pacientes.am, pacientes.birthdate, pacientes.alergias, pacientes.antecedentes, enfermedades.nombre, medicos.nombre, medicos.ap, medicos.am FROM pacientes inner join enfermedades on enfermedades.id=pacientes.enfermedad_id inner join medicos on pacientes.medico_id=medicos.id where medicos.id=%s order by pacientes.nombre ASC', (IDMED,))
    else:
        SPCS.execute('SELECT pacientes.id, pacientes.nombre, pacientes.ap, pacientes.am, pacientes.birthdate, pacientes.alergias, pacientes.antecedentes, enfermedades.nombre, medicos.nombre, medicos.ap, medicos.am FROM pacientes inner join enfermedades on enfermedades.id=pacientes.enfermedad_id inner join medicos on pacientes.medico_id=medicos.id ORDER BY pacientes.nombre ASC')
    QueryPacientes = SPCS.fetchall()
    return render_template('showPacientes.html', listPaciente=QueryPacientes, rolMedico=RMED, idMedico=IDMED)

# Editar paciente
@app.route('/editPaciente/<id>')
@login_required
def editPaciente(id):
    EPCS = mysql.connection.cursor()
    EPCS.execute('SELECT p.id, p.nombre, p.ap, p.am , p.birthdate, p.alergias, p.antecedentes, e.nombre, p.medico_id from pacientes p inner join enfermedades e on p.enfermedad_id = e.id where p.id = %s', (id,))
    QueryEPId = EPCS.fetchone()
    # Obtener lista de enfermedades
    enfermedades_cur = mysql.connection.cursor()
    enfermedades_cur.execute("SELECT * FROM enfermedades")
    lista_enfermedades = enfermedades_cur.fetchall()

    # Obtener lista de medicos con nombre completo
    medicos_cur = mysql.connection.cursor()
    medicos_cur.execute("SELECT id, CONCAT(nombre, ' ', ap, ' ', am) AS nombre_completo FROM medicos")
    lista_medicos = medicos_cur.fetchall()
    return render_template('editPaciente.html', listEPId=QueryEPId, enfermedades=lista_enfermedades, medicos=lista_medicos, rolMedico=RMED, idMedico=IDMED)

@app.route('/updatePaciente/<id>', methods=['POST'])
def updatePaciente(id):
    if request.method == 'POST':
        vnombre = request.form['txtnombre']
        vap = request.form['txtap']
        vam = request.form['txtam']
        vfechanacimiento = request.form['txtFechanacimiento']
        valergias = request.form['txtalergias']
        vantecedentes = request.form['txtantecedentes']
        venfermedad = int(request.form['txtEnfermedades']) 
        if RMED==1: 
            vmedico = IDMED 
        else:
            vmedico = int(request.form['txtmedico'])
        UpdPCur = mysql.connection.cursor()
        UpdPCur.execute('UPDATE pacientes SET nombre = %s, ap = %s, am = %s, birthdate = %s, alergias = %s, antecedentes = %s, enfermedad_id  = %s, medico_id = %s WHERE id = %s', (vnombre,vap,vam,vfechanacimiento,valergias,vantecedentes,venfermedad,vmedico,  id))
        mysql.connection.commit()
    flash('La información del paciente fue actualizada correctamente')
    return redirect(url_for('pacientes'))

# Eliminar paciente
@app.route('/delPaciente/<id>')
@login_required
def delPaciente(id):
    DPCS = mysql.connection.cursor()
    DPCS.execute('SELECT * FROM pacientes WHERE id = %s', (id,))
    QueryId = DPCS.fetchone()
    return render_template('deletePaciente.html', listIdDlt=QueryId)

@app.route('/deletePaciente/<id>', methods=['POST'])
def deletePaciente(id):
    if request.method == 'POST':
        if request.form.get('action') == 'delete':
            DelCur = mysql.connection.cursor()
            DelCur.execute('DELETE FROM pacientes WHERE id = %s', (id,))
            mysql.connection.commit()
            flash('El paciente fue eliminado correctamente')
        elif request.form.get('action') == 'cancel':
            flash('Eliminación cancelada')
    return redirect(url_for('pacientes'))

# Filter patients by name
@app.route('/filterPacientes', methods=['POST', 'GET'])
@login_required
def filterPacientes():
    if request.method == 'POST':
        search_name = request.form['search_name']
        SPCS = mysql.connection.cursor()
        
        if RMED == 1:
            SPCS.execute('SELECT pacientes.id, pacientes.nombre, pacientes.ap, pacientes.am, pacientes.birthdate, pacientes.alergias, pacientes.antecedentes, enfermedades.nombre, medicos.nombre, medicos.ap, medicos.am FROM pacientes INNER JOIN enfermedades ON enfermedades.id = pacientes.enfermedad_id INNER JOIN medicos ON pacientes.medico_id = medicos.id WHERE medicos.id = %s AND pacientes.nombre LIKE %s ORDER BY pacientes.nombre ASC', (IDMED, f"%{search_name}%"))
        else:
            SPCS.execute('SELECT pacientes.id, pacientes.nombre, pacientes.ap, pacientes.am, pacientes.birthdate, pacientes.alergias, pacientes.antecedentes, enfermedades.nombre, medicos.nombre, medicos.ap, medicos.am FROM pacientes INNER JOIN enfermedades ON enfermedades.id = pacientes.enfermedad_id INNER JOIN medicos ON pacientes.medico_id = medicos.id WHERE pacientes.nombre LIKE %s ORDER BY pacientes.nombre ASC', (f"%{search_name}%",))
        
        QueryPacientes = SPCS.fetchall()
        return render_template('showPacientes.html', listPaciente=QueryPacientes, rolMedico=RMED, idMedico=IDMED)

    return redirect(url_for('pacientes'))


###########################################  /PACIENTES  #####################################################

###########################################   EXPLORACIONES   #####################################################
@app.route('/exploraciones')
@login_required
def exploraciones():
    CC=mysql.connection.cursor()
    if RMED==1:
        CC.execute('SELECT exploraciones.id, Pacientes.Nombre, Pacientes.ap, Pacientes.am, round(DATEDIFF(NOW(), pacientes.birthdate)/365, 0) as Edad, Exploraciones.fecha, Exploraciones.peso, Exploraciones.altura, Exploraciones.altura, Exploraciones.temperatura, Exploraciones.latidos, Exploraciones.glucosa, Exploraciones.oxigeno FROM exploraciones inner join pacientes on exploraciones.paciente_id=pacientes.id where pacientes.medico_id=%s order by Exploraciones.fecha desc', (IDMED,))
    else:
        CC.execute('SELECT exploraciones.id, Pacientes.Nombre, Pacientes.ap, Pacientes.am, round(DATEDIFF(NOW(), pacientes.birthdate)/365, 0) as Edad, Exploraciones.fecha, Exploraciones.peso, Exploraciones.altura, Exploraciones.temperatura, Exploraciones.latidos, Exploraciones.glucosa, Exploraciones.oxigeno, medicos.nombre, medicos.ap, medicos.am FROM exploraciones inner join pacientes on exploraciones.paciente_id=pacientes.id inner join medicos on medicos.id=pacientes.medico_id order by Exploraciones.fecha desc')
    conExploraciones=CC.fetchall()
    return render_template('showExploraciones.html',listExploraciones=conExploraciones, rolMedico=RMED, idMedico=IDMED)

@app.route('/editExploraciones/<id>')
@login_required
def editExploraciones(id):
    EECS = mysql.connection.cursor()
    EECS.execute('SELECT * FROM Exploraciones WHERE id = %s', (id,))
    QueryEPId = EECS.fetchone()

    CP=mysql.connection.cursor()
    if RMED==2:
        CP.execute('SELECT id, nombre, ap, am from pacientes')
    else:
        CP.execute('SELECT id, nombre, ap, am from pacientes where medico_id=%s', (IDMED,))
    NomPacientes=CP.fetchall()
    return render_template('editExploraciones.html', Nombres=NomPacientes,exploracion=QueryEPId, rolMedico=RMED, idMedico=IDMED)

@app.route('/borrarExploraciones/<id>')
@login_required
def borrarExploraciones(id):
    EECS = mysql.connection.cursor()
    EECS.execute('SELECT * FROM Exploraciones WHERE id = %s', (id,))
    QueryEPId = EECS.fetchone()

    CP=mysql.connection.cursor()
    if RMED==2:
        CP.execute('SELECT id, nombre, ap, am from pacientes')
    else:
        CP.execute('SELECT id, nombre, ap, am from pacientes where medico_id=%s', (IDMED,))
    NomPacientes=CP.fetchall()
    return render_template('deleteExploraciones.html', Nombres=NomPacientes,exploracion=QueryEPId, rolMedico=RMED, idMedico=IDMED)

@app.route('/deleteExploraciones/<id>')
@login_required
def deleteExploraciones(id):
    DelCur = mysql.connection.cursor()
    DelCur.execute('DELETE FROM exploraciones WHERE id = %s', (id,))
    mysql.connection.commit()
    flash('La exploracion fue eliminada correctamente')
    return redirect(url_for('exploraciones'))

@app.route('/updateExploracion/<id>', methods=['POST'])
def updateExploracion(id):
    if request.method == 'POST':
        Vpaciente_id=request.form['txtpaciente']
        Vfecha= request.form['txtFecha']
        Vpeso= request.form['txtPeso']
        Valtura= request.form['txtAltura']
        Vtemperatura=request.form['txtTemperatura']
        Vlatidos=request.form['txtLatidos']
        Vglucosa=request.form['txtGlucosa']
        Voxigeno=request.form['txtOxigeno']
        CS = mysql.connection.cursor()
        CS.execute('UPDATE exploraciones set paciente_id=%s, fecha=%s, peso=%s, altura=%s, temperatura=%s, latidos=%s, glucosa=%s, oxigeno=%s where id=%s', (Vpaciente_id, Vfecha, Vpeso, Valtura, Vtemperatura,  Vlatidos, Vglucosa, Voxigeno, id))
        mysql.connection.commit()
    flash('La revision del paciente '+ Vpaciente_id + '  fue modificado correctamente' )
    return redirect(url_for('exploraciones'))

@app.route('/addExploracion')
@login_required
def addExploracion():
    CP=mysql.connection.cursor()
    if RMED==2:
        CP.execute('SELECT id, nombre, ap, am from pacientes')
    else:
        CP.execute('SELECT id, nombre, ap, am from pacientes where medico_id=%s', (IDMED,))
    NomPacientes=CP.fetchall()
    return render_template('addExploraciones.html', Nombres=NomPacientes,rolMedico=RMED, idMedico=IDMED)

@app.route('/guardarExploracion', methods=['POST'])
def guardarExploracion():
    if request.method == 'POST':
        Vpaciente_id=request.form['txtPaciente_id']
        Vfecha= request.form['txtFecha']
        Vpeso= request.form['txtPeso']
        Valtura= request.form['txtAltura']
        Vtemperatura=request.form['txtTemperatura']
        Vlatidos=request.form['txtLatidos']
        Vglucosa=request.form['txtGlucosa']
        Voxigeno=request.form['txtOxigeno']
        CS = mysql.connection.cursor()
        CS.execute('insert into exploraciones (paciente_id, fecha, peso, altura, temperatura, latidos, glucosa, oxigeno) values (%s, %s, %s, %s, %s, %s, %s, %s)',(Vpaciente_id, Vfecha, Vpeso, Valtura, Vtemperatura, Vlatidos, Vglucosa, Voxigeno))
        mysql.connection.commit()
    flash('La exploración fue agregada correctamente')
    return redirect(url_for('exploraciones'))
###########################################   /EXPLORACIONES   #####################################################


###########################################   Enfermedades   #####################################################
@app.route('/addEnfermedades')
@login_required
def addEnfermedades():
    return render_template('addEnfermedades.html', rolMedico=RMED, idMedico=IDMED)

# Agregar un nueva nueva enfermedad al catalogo de enfermedades
@app.route('/guardarEnfermedad', methods=['POST'])
def guardarEnfermedad():
    if request.method == 'POST':
        # pasamos a variables el contenido de los input
        vnombre = request.form['txtnombre']
        CSGE = mysql.connection.cursor()  # objeto de tipo cursor
        CSGE.execute('INSERT INTO enfermedades ( nombre) VALUES (%s)', ( vnombre,))
        mysql.connection.commit()
    flash('Enfermedad registrada exitosamente')
    return redirect(url_for('addPacientes'))

###########################################   /Enfermedades   #####################################################


###########################################   Citas   #####################################################

@app.route('/citas')
@login_required
def citas():
    CC=mysql.connection.cursor()
    if RMED==1:
        CC.execute('select p.nombre, p.ap, p.am, e.fecha, e.id from exploraciones e inner join pacientes p on e.paciente_id = p.id where p.medico_id= %s', (IDMED,))
    else:
        CC.execute('select p.nombre, p.ap, p.am, e.fecha, e.id, m.nombre, m.ap, m.am from exploraciones e inner join pacientes p on e.paciente_id = p.id inner join medicos m on p.medico_id = m.id')
    conCitas=CC.fetchall()
    return render_template('showCitas.html',listCitas=conCitas, rolMedico=RMED, idMedico=IDMED)
"""
@app.route('/editCitas', methods=['POST'])
@login_required
def editCitas():

    CC=mysql.connection.cursor()
    CC.execute('select * from exploraciones where ')


    return render_template('editCitas.html', rolMedico=RMED, idMedico=IDMED)

@app.route('/updateCitas')
@login_required
def updateCitas():
    return redirect(url_for('editCitas'))

@app.route('/eliminarCitas')
@login_required
def eliminarCitas():
    return render_template('deleteCitas.html', rolMedico=RMED, idMedico=IDMED)

@app.route('/deleteCitas')
@login_required
def deleteCitas():
    return redirect(url_for('eliminarCitas'))
"""


@app.route('/citas_por_fecha', methods=['GET', 'POST'])
@login_required
def citas_por_fecha():
    if request.method == 'POST':
        fecha_filtro = request.form.get('fecha_filtro')  # Obtener la fecha ingresada en el formulario
        CC = mysql.connection.cursor()
        
        if RMED == 1:
            CC.execute('SELECT p.nombre, p.ap, p.am, e.fecha, e.id FROM exploraciones e INNER JOIN pacientes p ON e.paciente_id = p.id WHERE p.medico_id = %s AND e.fecha = %s', (IDMED, fecha_filtro))
        else:
            CC.execute('SELECT p.nombre, p.ap, p.am, e.fecha, e.id, m.nombre, m.ap, m.am FROM exploraciones e INNER JOIN pacientes p ON e.paciente_id = p.id INNER JOIN medicos m ON p.medico_id = m.id WHERE e.fecha = %s', (fecha_filtro,))
        
        conCitas = CC.fetchall()
        return render_template('showCitas.html', listCitas=conCitas, rolMedico=RMED, idMedico=IDMED)
    
    return render_template('filtroCitas.html')  # Renderizar un formulario para ingresar la fecha de filtro

###########################################   /Citas   #####################################################

###########################################   pdf   ######################################################



@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    exploraciones = request.form.get('exp_id')
    cur = mysql.connection.cursor()
    cur.execute('select p.nombre, p.ap, p.am, e.fecha, e.peso, e.altura, e.temperatura, e.latidos, e.glucosa, e.oxigeno, d.tratamiento,d.medicamentos, d.indicaciones, m.nombre, m.ap, m.am, m.cedula, p.alergias from exploraciones e inner join pacientes p on e.paciente_id = p.id inner join diagnosticos d on e.id = d.expediente_id inner join medicos m on p.medico_id = m.id where e.id = %s ',(exploraciones,))
    data = cur.fetchall()
    cur.close()

    pdf_filename = generar_reporte_pdf(data)

    return send_file(pdf_filename, as_attachment=True)


def mm_to_points(mm):
    return mm / 0.3527



def draw_text_with_word_wrap(c, x, y, text, max_width, line_height):
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        test_width = c.stringWidth(test_line, "Times-Roman", 15)
        
        if test_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    
    lines.append(current_line)
    
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
        
        

def generar_reporte_pdf(data):
    template_path = "static/template.pdf"
    pdf_filename = "receta_medica.pdf"
    
    packet = io.BytesIO()
    # Create a new PDF with reportlab
    c = canvas.Canvas(packet, pagesize=portrait((1000*mm_to_points(1), 1000*mm_to_points(1))))  # Tamaño personalizado en puntos
    c.setFont("Times-Roman", 15)

    c.drawString(980, 650, f"Fecha: {data[0][3]}")

    paciente_info = f"{data[0][0]} {data[0][1]} {data[0][2]}"
    c.drawString(70, 650, 'PACIENTE:')
    c.drawString(150, 650, paciente_info)
    
    doc_info = f"{data[0][13]} {data[0][14]} {data[0][15]}"
    c.drawString(950, 750, 'Dr.')
    c.drawString(975, 750, doc_info)
    
    c.drawString(950, 700, f"Cedula: {data[0][16]}")
    

    c.drawString(70, 580, 'EXPLORACION:')
    y_position = 550
    exploracion_labels = [
        "Peso (Kg):", "Altura (M):", "Temp (C):", "Latidos:", "Glucosa:", "SATO2:"
    ]
    exploracion_data = data[0][4:10]
    for label, value in zip(exploracion_labels, exploracion_data):
        c.drawString(70, y_position, label)
        c.drawString(150, y_position, str(value))
        y_position -= 25
    
    c.drawString(70, y_position - 20, 'Alergias:')
    c.drawString(70, y_position - 40, data[0][17])
        
        
    max_text_width = 700  # Establece el ancho máximo para el texto
    # Dibujar el tratamiento, medicamentos e indicaciones con ajuste de línea
    c.drawString(595.98, 580, 'Tratamiento:')
    draw_text_with_word_wrap(c, 280, 580 - 20, data[0][10], max_text_width, 20)

    c.drawString(595.98, 500, 'Medicamentos:')
    draw_text_with_word_wrap(c, 280, 500 - 40, data[0][11], max_text_width, 20)
    
    c.drawString(595.98, 420.69, 'Indicaciones:')
    draw_text_with_word_wrap(c, 280, 420 - 40, data[0][12], max_text_width, 20)

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


###########################################   /pdf   #####################################################


if __name__ == '__main__':
    app.run(port=5000,debug=True)