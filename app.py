from flask import Flask,render_template, request, redirect, url_for, session
from flask_session import Session
import pandas as pd
from flask_mysqldb import MySQL
import pickle
import gzip
import json
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer
tfidf_vectorizer = TfidfVectorizer()

app = Flask(__name__)
app.secret_key = '830245d3f139432a1b3f9e8dd31a30541fbbcd0b879c6433' 
# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'theLonewolf_20'
app.config['MYSQL_DB'] = 'pathvista'
mysql = MySQL(app)

with gzip.open('data.pkl.gz', 'rb') as f:
    data = pickle.load(f)
    
df_final_person = data['Final']
df_all = data['All']
df_jobs = data['Jobs']
java_output = data['Java']
cashier_output = data['Cashier']
ds_output = data['DS']
intern_output = data['Intern']
mang_output = data['Manager']
sr_output = data['SR']
teacher_output = data['Teacher']

tfidf_jobid = tfidf_vectorizer.fit_transform((df_all['text'])) 

with open('matched_data.json', 'r') as json_file:
    matched_data_values = json.load(json_file)

def find_output(u):
    if(u ==11): return cashier_output
    if(u==222): return ds_output
    if(u==120): return intern_output
    if(u==326): return java_output
    if(u==146): return mang_output
    if(u==113): return sr_output
    if(u==194): return teacher_output
    return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/signsubmit', methods = ['POST'])
def signsubmit():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        name = fname + " " + lname
        mail = request.form['mail']
        password = request.form['password']
        position = request.form['position']
        connection = mysql.connect
        cur = connection.cursor()
        # Check if the email already exists
        cur.execute("SELECT COUNT(*) FROM pvdetails WHERE mailid = %s", (mail,))
        email_exists = cur.fetchone()[0]
        if email_exists > 0:
            return redirect(url_for('ext'))
        else:
            # Email does not exist, proceed with the insertion
            cur.execute("INSERT INTO pvdetails VALUES(%s, %s, %s, %s)", (name, mail, password,position))
            connection.commit()
            cur.close()
            # Check if the row was successfully inserted
            if cur.rowcount > 0:
                return redirect(url_for('loading1'))
            else:
                # Handle the situation where the insertion failed
                return redirect(url_for('/'))

@app.route('/loading1')
def loading1():
    return render_template('loading1.html')

@app.route('/ext')
def ext():
    return render_template('ext.html')

@app.route('/failed')
def failed():
    return render_template('failed.html')

def retrieve_additional_data(user_id):
    connection = mysql.connect
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM pvdetails WHERE mailid = %s", (user_id,))
    additional_data = cursor.fetchone()
    cursor.close()
    connection.close()
    return additional_data

@app.route('/submit', methods = ['POST'])
def submit():
    if request.method == 'POST':
        mail = request.form['mail']
        password = request.form['password']
        connection = mysql.connect
        cur = connection.cursor()
        cur.execute("SELECT mailid,password FROM pvdetails WHERE mailid = %s and password = %s", (mail,password))
        user = cur.fetchone()
        cur.close()
        if user:
            additional_data = retrieve_additional_data(mail)
            print(additional_data)
            session['user'] = {'mailid': mail, 'additional_data': additional_data}
            return redirect(url_for('loading2'))
        else:
            return redirect(url_for('failed'))

@app.route('/loading2')
def loading2():
    return render_template('loading2.html')

def search_data(query):
    results = []
    for data, value in matched_data_values:
        # Check if the query matches either the data or the numerical value
        if query.lower() in data.lower() or str(query) == str(value):
            results.append((data, value))
    return results[0][1]

def get_jobs(u):
    output = find_output(u)
    def get_recommendation(top, df_all, scores):
        recommendation = pd.DataFrame(columns = ['ApplicantID', 'JobID',  'title', 'score'])
        count = 0
        for i in top:
            recommendation.at[count, 'ApplicantID'] = u
            recommendation.at[count, 'JobID'] = df_all['Job.ID'][i]
            recommendation.at[count, 'title'] = df_all['Title'][i]
            recommendation.at[count, 'score'] =  scores[count]
            count += 1
        return recommendation
    top = sorted(range(len(output)), key=lambda i: output[i], reverse=True)[:15]
    list_scores = [output[i][0][0] for i in top]
    results = get_recommendation(top,df_all, list_scores)
    results_sorted = results.sort_values(by='score', ascending=False)
    # Extract the JobID values
    job_ids = results_sorted['JobID'].values
    # Filter out the matching jobs from the full details DataFrame
    matching_jobs_df = df_jobs[df_jobs['Job.ID'].isin(job_ids)]
    return matching_jobs_df

@app.route('/profile')
def profile():
    if 'user' in session:
        # Retrieve user information from the session
        user_info = session['user']
        # Example: Access mailid and additional data
        mailid = user_info.get('mailid', 'Default Mailid')
        additional_data = user_info.get('additional_data', 'Default Additional Data')
        vdata = additional_data[3]
        ndata = search_data(vdata)
        # print(type(ndata))
        u_jobs = get_jobs(ndata)
        user_jobs = u_jobs.to_dict(orient='records')
        additional_data = user_info.get('additional_data', 'Default Additional Data')
        # Pass the data to the template
        return render_template('profile.html', mailid=mailid, additional_data=additional_data, user_jobs=user_jobs)
    else:
        return redirect(url_for('signin'))
    
@app.route('/logout')
def logout():
    return redirect(url_for('signin'))
    
    
if __name__ == '__main__':
    app.run(debug=True)