from distutils.log import debug
from flask import Flask,flash, request,redirect,render_template, url_for, session
import ibm_db
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import re
import urllib.request
from werkzeug.utils import secure_filename
from flask import Flask,render_template
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2
import requests
import base64

#connection with db
try:
    conn = ibm_db.connect("DATABASE=bludb;HOSTNAME=9938aec0-8105-433e-8bf9-0fbb7e483086.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud;PORT=32459;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;PROTOCOL=TCPIP;UID=yjt37774;PWD=A3pQPlackJvoE1tv;",'','')
    print(conn)
    print("connection successfull")
except:
    print("Error in connection, sqlstate = ")
    errorState = ibm_db.conn_error()
    print(errorState)

app = Flask(__name__,static_url_path='/static')
app.secret_key = 'smartfashionrecommender'


#to load env
load_dotenv()



@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))
#Clarifai api
C_USER_ID = os.getenv('C_USER_ID')
# Your PAT (Personal Access Token) can be found in the portal under Authentification
C_PAT = os.getenv('C_PAT')
C_APP_ID = os.getenv('C_APP_ID')
C_MODEL_ID = 'food-item-recognition'

@app.route('/plans')
def plans():
    return render_template('plans.html')
@app.route('/nutrition')
def nutrition():
    return render_template('nutrition.html')
@app.route('/login',methods=['GET','POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        checkuser = "SELECT * FROM USERS WHERE email=? AND password=?"
        stmt1 = ibm_db.prepare(conn,checkuser)
        ibm_db.bind_param(stmt1,1,email)
        ibm_db.bind_param(stmt1,2,password)
        ibm_db.execute(stmt1)
        account = ibm_db.fetch_tuple(stmt1)
        if account:
            #user has an account
            session['loggedin'] = True
            session['id'] = account[0]
            session['username'] = account[1]
            # msg = "logged in successfull" ( Need to set timoeout to display this message )
            return redirect(url_for('home'))
        else:
            msg = "Invalid email-id or password!"
    return render_template("sign_in.html",msg=msg)

# Helper function to send confirmation mail on sign in
def send_confirmation_mail(username, email):
    message = Mail(
        from_email="assistantnutri68@gmail.com",
        to_emails=email,
        subject="YAYY!! Your Account was created successfully!",
        # html_content= "<strong>Account Created with username {0}</strong>".format(username)
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print("does not send email")
        print(e)

# http://localhost:5000/python/logout - this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/signup',methods=['GET','POST'])
def sign_up():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        print(username,email,password)
        checkuser = "SELECT email FROM USERS WHERE email=?"
        stmt1 = ibm_db.prepare(conn,checkuser)
        ibm_db.bind_param(stmt1,1,email)
        ibm_db.execute(stmt1)
        account = ibm_db.fetch_tuple(stmt1)
        print(account)
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            sql = "INSERT INTO USERS(username,password,email) VALUES(?,?,?)"
            stmt = ibm_db.prepare(conn,sql)
            ibm_db.bind_param(stmt, 1, username)
            ibm_db.bind_param(stmt, 2, password)
            ibm_db.bind_param(stmt, 3, email)
            ibm_db.execute(stmt)
            print(username,email,password)
            msg = 'You have successfully registered!'
            send_confirmation_mail(username, email)
            return redirect(url_for('home'))
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('sign_up.html', msg=msg)
    
UPLOAD_FOLDER = 'assets/uploads/'
 
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
API_URL="https://api.imgbb.com/1/upload"

@app.route('/upload', methods=['POST','GET'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        print(file)
        if file.filename == '':
            flash('No image selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename=secure_filename(file.filename)
            api_data = {
                'key': "7dfb136dd63e7888412ca2ba061135c9",
                'image': base64.b64encode(file.read()),
                'name': filename
            }
            r = requests.post(url = API_URL, data = api_data)
            rj = r.json()        
            url = rj.get('data').get('display_url')
            #print('upload filename: ' + filename)
            print('Image successfully uploaded and displayed below')
            # predict(url)
            return render_template('upload.html', filename=url)
        else:
            flash('Allowed image types are - png, jpg, jpeg, gif')
            return redirect(request.url)
    elif request.method == 'GET':
        return render_template('upload.html')

@app.route('/display/<filename>')
def display_image(filename):
    #print('display_image filename: ' + filename)
    return redirect(filename, code=301)
    #return render_template('food.html')



 
if __name__ == '__main__':
    app.run(debug=True)