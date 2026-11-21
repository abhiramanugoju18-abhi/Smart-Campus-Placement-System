from django.shortcuts import render
from django.template import RequestContext
from django.contrib import messages
from django.http import HttpResponse
import os
import pickle
import pymysql
import os
from django.core.files.storage import FileSystemStorage
from datetime import date
from django.shortcuts import render
from django.http import HttpResponse
import pymysql
import os
from datetime import date

# ================= DATABASE CONNECTION =================
def db():
    return pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='root',
        database='placement',
        charset='utf8'
    )

# ================= COMMON FUNCTIONS =================
def getCompany(job_id):
    con = db()
    with con:
        cur = con.cursor()
        cur.execute("SELECT company_name FROM jobs WHERE job_id=%s", (job_id,))
        row = cur.fetchone()
        return row[0] if row else ""

def getScore(student_name):
    con = db()
    with con:
        cur = con.cursor()
        cur.execute("SELECT score FROM profile WHERE student_name=%s", (student_name,))
        row = cur.fetchone()
        return row[0] if row else ""

# ================= VIEW PERFORMANCE (COMPANY) =================
def ViewPerformance(request):
    uname = request.session.get('uname')
    if not uname:
        return render(request, 'CompanyLogin.html',
                      {'data': 'Session expired. Please login again.'})

    output = """
    <table border=1 width=100%>
    <tr>
        <th>Job ID</th>
        <th>Student Name</th>
        <th>Status</th>
        <th>Score</th>
    </tr>
    """

    con = db()
    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT a.job_id, a.student_name, a.status, p.score
            FROM applyjob a
            JOIN jobs j ON a.job_id=j.job_id
            LEFT JOIN profile p ON a.student_name=p.student_name
            WHERE j.company_name=%s
        """, (uname,))
        for r in cur.fetchall():
            output += f"""
            <tr>
                <td>{r[0]}</td>
                <td>{r[1]}</td>
                <td>{r[2]}</td>
                <td>{r[3]}</td>
            </tr>
            """

    output += "</table>"
    return render(request, 'CompanyScreen.html', {'data': output})

# ================= VIEW FEEDBACK (TPO) =================
def ViewFeedback(request):
    output = "<table border=1 width=100%><tr><th>Student</th><th>Feedback</th></tr>"
    con = db()
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM feedback")
        for row in cur.fetchall():
            output += f"<tr><td>{row[0]}</td><td>{row[1]}</td></tr>"
    output += "</table>"
    return render(request, 'TPOScreen.html', {'data': output})

# ================= JOB STATUS (STUDENT) =================
def JobStatus(request):
    uname = request.session.get('uname')
    if not uname:
        return render(request, 'StudentLogin.html',
                      {'data': 'Session expired. Please login again.'})

    output = "<table border=1 width=100%><tr><th>Job ID</th><th>Name</th><th>Status</th></tr>"
    con = db()
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM applyjob WHERE student_name=%s", (uname,))
        for row in cur.fetchall():
            output += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>"
    output += "</table>"
    return render(request, 'StudentScreen.html', {'data': output})

# ================= APPLY JOB =================
def ApplyJob(request):
    job_id = request.GET.get('id')
    output = f"<tr><td>Job ID <input name='job' value='{job_id}'></td></tr>"
    correct = []

    con = db()
    with con:
        cur = con.cursor()
        cur.execute("SELECT * FROM questions")
        i = 0
        for q, a, b, c, d, ans in cur.fetchall():
            output += f"""
            <tr><td><b>{q}</b></td></tr>
            <tr><td>{a} <input type="radio" name="t{i+1}" value="A"></td></tr>
            <tr><td>{b} <input type="radio" name="t{i+1}" value="B"></td></tr>
            <tr><td>{c} <input type="radio" name="t{i+1}" value="C"></td></tr>
            <tr><td>{d} <input type="radio" name="t{i+1}" value="D"></td></tr>
            """
            correct.append(ans)
            i += 1

    request.session['correct_answers'] = correct
    return render(request, 'ExamTest.html', {'data1': output})

# ================= EXAM SUBMIT =================
def ExamTestAction(request):
    uname = request.session.get('uname')
    correct = request.session.get('correct_answers')

    if not uname or not correct:
        return render(request, 'StudentLogin.html',
                      {'data': 'Session expired. Please login again.'})

    job_id = request.POST.get('job')
    total = 0

    for i in range(len(correct)):
        if request.POST.get("t"+str(i+1)) == correct[i]:
            total += 1

    score = total / len(correct)
    status = "Selected" if score >= 0.8 else "Rejected"

    con = db()
    with con:
        cur = con.cursor()
        cur.execute("UPDATE profile SET score=%s WHERE student_name=%s",
                    (str(score), uname))
        cur.execute("INSERT INTO applyjob VALUES(%s,%s,%s)",
                    (job_id, uname, status))
        con.commit()

    del request.session['correct_answers']
    return render(request, 'StudentScreen.html',
                  {'data': f'<font color=blue>Score : {score}</font>'})

# ================= LOGIN =================
def StudentLoginAction(request):
    username = request.POST.get('t1')
    password = request.POST.get('t2')

    con = db()
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM register
                       WHERE username=%s AND password=%s AND usertype='Student'""",
                    (username, password))
        if cur.fetchone():
            request.session['uname'] = username
            request.session.modified = True
            return render(request, 'StudentScreen.html',
                          {'data': f'Welcome {username}'})

    return render(request, 'StudentLogin.html', {'data': 'login failed'})

def CompanyLoginAction(request):
    username = request.POST.get('t1')
    password = request.POST.get('t2')

    con = db()
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM register
                       WHERE username=%s AND password=%s AND usertype='Company'""",
                    (username, password))
        if cur.fetchone():
            request.session['uname'] = username
            request.session.modified = True
            return render(request, 'CompanyScreen.html',
                          {'data': f'Welcome {username}'})

    return render(request, 'CompanyLogin.html', {'data': 'login failed'})

def TPOLoginAction(request):
    username = request.POST.get('t1')
    password = request.POST.get('t2')

    con = db()
    with con:
        cur = con.cursor()
        cur.execute("""SELECT * FROM register
                       WHERE username=%s AND password=%s AND usertype='TPO'""",
                    (username, password))
        if cur.fetchone():
            request.session['uname'] = username
            request.session.modified = True
            return render(request, 'TPOScreen.html',
                          {'data': f'Welcome {username}'})

    return render(request, 'TPOLogin.html', {'data': 'login failed'})

# ================= SIMPLE PAGE LOADS =================
def index(request): return render(request, 'index.html')
def StudentLogin(request): return render(request, 'StudentLogin.html')
def CompanyLogin(request): return render(request, 'CompanyLogin.html')
def TPOLogin(request): return render(request, 'TPOLogin.html')
def Register(request): return render(request, 'Register.html')
def Feedback(request): return render(request, 'Feedback.html')
def AddQuestion(request): return render(request, 'AddQuestion.html')
def PostJob(request): return render(request, 'PostJob.html')



def getCompany(job_id):
    company = ""
    con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
    with con:
        cur = con.cursor()
        cur.execute("select company_name from jobs where job_id='"+str(job_id)+"'")
        rows = cur.fetchall()
        for row in rows:
            company = row[0]
            break
    return company

def getScore(student_name):
    score = ""
    con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
    with con:
        cur = con.cursor()
        cur.execute("select score from profile where student_name='"+student_name+"'")
        rows = cur.fetchall()
        for row in rows:
            score = row[0]
            break
    return score

def ViewPerformance(request):
    uname = request.session.get('uname')

    if not uname:
        return render(
            request,
            'CompanyLogin.html',
            {'data': 'Session expired. Please login again.'}
        )

    con = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='root',
        database='placement',
        charset='utf8'
    )

    output = '''
    <table border="1" width="100%">
    <tr>
        <th>Job ID</th>
        <th>Student Name</th>
        <th>Status</th>
        <th>Exam Score</th>
    </tr>
    '''

    with con:
        cur = con.cursor()
        cur.execute("""
            SELECT a.job_id, a.student_name, a.status, p.score
            FROM applyjob a
            JOIN jobs j ON a.job_id = j.job_id
            LEFT JOIN profile p ON a.student_name = p.student_name
            WHERE j.company_name = %s
        """, (uname,))

        rows = cur.fetchall()
        for r in rows:
            output += f"""
            <tr>
                <td>{r[0]}</td>
                <td>{r[1]}</td>
                <td>{r[2]}</td>
                <td>{r[3]}</td>
            </tr>
            """

    output += "</table>"

    return render(request, 'CompanyScreen.html', {'data': output})



def ViewFeedback(request):
    if request.method == 'GET':
    
        output = ''
        output+='<table border=1 align=center width=100%><tr><th><font size="3" color="black">Student name</th><th><font size="3" color="black">Challenges Feedback</th>'
        output+='</tr>'
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
        with con:    
            cur = con.cursor()
            cur.execute("select * from feedback")
            rows = cur.fetchall()
            for row in rows:
                output+='<tr><td><font size="3" color="black">'+str(row[0])+'</td><td><font size="3" color="black">'+str(row[1])+'</td></tr>'
        output+= "</table></br></br></br></br>"        
        context= {'data':output}
        return render(request, 'TPOScreen.html', context) 

def JobStatus(request):
    if request.method == 'GET':
        uname = request.session.get('uname')

        if not uname:
            return render(
                request,
                'StudentLogin.html',
                {'data': 'Session expired. Please login again.'}
            )

        output = ''
        output += '<table border=1 align=center width=100%>'
        output += '<tr>'
        output += '<th><font size="3" color="black">Job ID</th>'
        output += '<th><font size="3" color="black">Student Name</th>'
        output += '<th><font size="3" color="blue">Status</th>'
        output += '</tr>'

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )

        with con:
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM applyjob WHERE student_name=%s",
                (uname,)
            )
            rows = cur.fetchall()

            for row in rows:
                output += (
                    f"<tr>"
                    f"<td><font size='3'>{row[0]}</td>"
                    f"<td><font size='3'>{row[1]}</td>"
                    f"<td><font size='3'>{row[2]}</td>"
                    f"</tr>"
                )

        output += "</table><br><br>"

        return render(request, 'StudentScreen.html', {'data': output})


def checkApplicationStatus(job_id, uname):
    con = pymysql.connect(
        host='127.0.0.1', port=3306,
        user='root', password='root',
        database='placement', charset='utf8'
    )
    with con:
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM applyjob WHERE job_id=%s AND student_name=%s",
            (job_id, uname)
        )
        return cur.fetchone() is not None


# def runKNNML(skills, uname):
#     recommendation = []

#     # normalize student skills
#     b = [x.strip().lower() for x in skills.split(",")]

#     con = pymysql.connect(
#         host='127.0.0.1',
#         port=3306,
#         user='root',
#         password='root',
#         database='placement',
#         charset='utf8'
#     )

#     with con:
#         cur = con.cursor()
#         cur.execute("SELECT * FROM jobs")
#         rows = cur.fetchall()

#         for row in rows:
#             job_id = str(row[0])

#             # skip if already applied
#             cur.execute(
#                 "SELECT * FROM applyjob WHERE job_id=%s AND student_name=%s",
#                 (job_id, uname)
#             )
#             if cur.fetchone():
#                 continue

#             # normalize job skills
#             a = [x.strip().lower() for x in row[6].split(",")]

#             match = len(set(a).intersection(b))
#             if match > 0:
#                 score = match / len(set(a))
#                 recommendation.append([
#                     job_id, row[1], row[2], row[3],
#                     row[4], row[5], row[6], score
#                 ])

#     recommendation.sort(key=lambda x: x[7], reverse=True)
#     return recommendation



def ExamTestAction(request):
    if request.method == 'POST':
        uname = request.session.get('uname')
        correct = request.session.get('correct_answers')

        if not uname or not correct:
            return render(
                request,
                'StudentLogin.html',
                {'data': 'Session expired. Please try again.'}
            )

        job_id = request.POST.get('job')
        total = 0

        for i in range(len(correct)):
            user_answer = request.POST.get("t"+str(i+1))
            if user_answer == correct[i]:
                total += 1

        total = total / len(correct) if len(correct) > 0 else 0
        status = "Selected" if total > 0.80 else "Rejected"

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )
        cur = con.cursor()

        cur.execute(
            "UPDATE profile SET score=%s WHERE student_name=%s",
            (str(total), uname)
        )

        cur.execute(
            "INSERT INTO applyjob VALUES(%s,%s,%s)",
            (job_id, uname, status)
        )

        con.commit()

        # optional cleanup
        del request.session['correct_answers']

        return render(
            request,
            'StudentScreen.html',
            {'data': f'<font size=3 color=blue>Your total marks = {total}</font>'}
        )
    

def ApplyJob(request):
    if request.method == 'GET':
        job_id = request.GET.get('id')
        output = '<tr><td>Job ID <input name="job" value="'+job_id+'"></td></tr>'

        correct_answers = []   # local list

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )

        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM questions")
            rows = cur.fetchall()

            i = 0
            for row in rows:
                question, a, b, c, d, answer = row

                output += f"""
                <tr><td><b>{question}</b></td></tr>
                <tr><td>{a} <input type="radio" name="t{i+1}" value="A"></td></tr>
                <tr><td>{b} <input type="radio" name="t{i+1}" value="B"></td></tr>
                <tr><td>{c} <input type="radio" name="t{i+1}" value="C"></td></tr>
                <tr><td>{d} <input type="radio" name="t{i+1}" value="D"></td></tr>
                """

                correct_answers.append(answer)
                i += 1

        # ✅ STORE IN SESSION
        request.session['correct_answers'] = correct_answers

        return render(request, 'ExamTest.html', {'data1': output})

def Recommendation(request):
    if request.method == 'GET':
        uname = request.session.get('uname')

        if not uname:
            return render(
                request,
                'StudentLogin.html',
                {'data': 'Session expired. Please login again.'}
            )

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )

        output = ''
        output += '<table border=1 align=center width=100%>'
        output += '<tr>'
        output += '<th>Job ID</th>'
        output += '<th>Company</th>'
        output += '<th>Description</th>'
        output += '<th>Salary</th>'
        output += '<th>Posted Date</th>'
        output += '<th>Last Date</th>'
        output += '<th>Required Skills</th>'
        output += '<th>Apply</th>'
        output += '</tr>'

        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM jobs")
            rows = cur.fetchall()

            for row in rows:
                job_id = row[0]

                output += f"""
                <tr>
                    <td>{row[0]}</td>
                    <td>{row[1]}</td>
                    <td>{row[2]}</td>
                    <td>{row[3]}</td>
                    <td>{row[4]}</td>
                    <td>{row[5]}</td>
                    <td>{row[6]}</td>
                    <td>
                        <a href="ApplyJob?id={job_id}">
                            <font color="red">Apply</font>
                        </a>
                    </td>
                </tr>
                """

        output += '</table><br><br>'

        return render(request, 'StudentScreen.html', {'data': output})


def Feedback(request):
    if request.method == 'GET':
       return render(request, 'Feedback.html', {})

def FeedbackAction(request):
    if request.method == 'POST':
        uname = request.session.get('uname')

        if not uname:
            return render(
                request,
                'StudentLogin.html',
                {'data': 'Session expired. Please login again.'}
            )

        feedback = request.POST.get('t1')

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )
        cur = con.cursor()

        cur.execute(
            "INSERT INTO feedback VALUES(%s,%s)",
            (uname, feedback)
        )
        con.commit()

        return render(
            request,
            'Feedback.html',
            {'data': '<font size=3 color=blue>Your feedback accepted successfully</font>'}
        )

def AddQuestion(request):
    if request.method == 'GET':
       return render(request, 'AddQuestion.html', {})  

def PostJob(request):
    if request.method == 'GET':
       return render(request, 'PostJob.html', {})    

def CompanyLogin(request):
    if request.method == 'GET':
       return render(request, 'CompanyLogin.html', {})    

def TPOLogin(request):
    if request.method == 'GET':
       return render(request, 'TPOLogin.html', {})

def StudentLogin(request):
    if request.method == 'GET':
       return render(request, 'StudentLogin.html', {})

def Register(request):
    if request.method == 'GET':
       return render(request, 'Register.html', {})    

def index(request):
    if request.method == 'GET':
        return render(request, 'index.html', {})   

def TPOLoginAction(request):
    if request.method == 'POST':
     
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        index = 0
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
        with con:    
            cur = con.cursor()
            cur.execute("select * FROM register where username='"+username+"' and password='"+password+"' and usertype='TPO'")
            rows = cur.fetchall()
            for row in rows:
                uname = username
                utype = row[0]
                index = 1
                break		
        if index == 1:
            context= {'data':'<font size=3 color=blue>Welcome '+username+"</font>"}
            return render(request, 'TPOScreen.html', context)
        else:
            context= {'data':'login failed'}
            return render(request, 'TPOLogin.html', context)        
    
from django.shortcuts import render, redirect

def CompanyLoginAction(request):
    if request.method == 'POST':

        username = request.POST.get('t1')
        password = request.POST.get('t2')
        index = 0

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )

        with con:
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM register WHERE username=%s AND password=%s AND usertype='Company'",
                (username, password)
            )
            if cur.fetchone():
                index = 1

        if index == 1:
            # ✅ STORE SESSION (CRITICAL)
            request.session['uname'] = username
            request.session.modified = True

            # ✅ REDIRECT (DO NOT render)
            return redirect('CompanyScreen')

        else:
            return render(
                request,
                'CompanyLogin.html',
                {'data': 'login failed'}
            )
        
def CompanyScreen(request):
    uname = request.session.get('uname')

    if not uname:
        return render(
            request,
            'CompanyLogin.html',
            {'data': 'Session expired. Please login again.'}
        )

    return render(request, 'CompanyScreen.html')


def StudentLoginAction(request):
    if request.method == 'POST':
        username = request.POST.get('t1')
        password = request.POST.get('t2')

        con = pymysql.connect(
            host='127.0.0.1', port=3306,
            user='root', password='root',
            database='placement', charset='utf8'
        )
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM register WHERE username=%s AND password=%s AND usertype='Student'",
            (username, password)
        )

        if cur.fetchone():
            request.session['uname'] = username
            request.session.modified = True  # ✅ THIS LINE IS CRITICAL
            return render(
                request,
                'StudentScreen.html',
                {'data': f'<font size=3 color=blue>Welcome {username}</font>'}
            )

        return render(request, 'StudentLogin.html', {'data': 'login failed'})

def RegisterAction(request):
    if request.method == 'POST':
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        contact = request.POST.get('t3', False)
        email = request.POST.get('t4', False)
        address = request.POST.get('t5')
        utype = request.POST.get('t6', False)
        
        status = "none"
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
        with con:    
            cur = con.cursor()
            cur.execute("select username FROM register")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == username:
                    status = username+" username already exists"
                    break
        if status == "none":
            db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "INSERT INTO register VALUES('"+username+"','"+password+"','"+contact+"','"+email+"','"+address+"','"+utype+"')"
            db_cursor.execute(student_sql_query)
            db_connection.commit()
            if db_cursor.rowcount == 1:
                status = "<font size=3 color=blue>Signup process successfully completed</font>"
            else:
                status = "error in signup"      
        else:
            status = "error in signup"        
        context= {'data': status}
        return render(request, 'Register.html', context)

def AddQuestionAction(request):
    if request.method == 'POST':
    
        question = request.POST.get('t1', False)
        a = request.POST.get('t2', False)
        b = request.POST.get('t3', False)
        c = request.POST.get('t4', False)
        d = request.POST.get('t5', False)
        answer = request.POST.get('t6', False)
        db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'placement',charset='utf8')
        db_cursor = db_connection.cursor()
        student_sql_query = "INSERT INTO questions VALUES('"+question+"','"+a+"','"+b+"','"+c+"','"+d+"','"+answer+"')"
        db_cursor.execute(student_sql_query)
        db_connection.commit()
        status = "<font size=3 color=blue>Question details added successfully</font>"
        context= {'data': status}
        return render(request, 'AddQuestion.html', context)    

def PostJobAction(request):
    if request.method == 'POST':
        uname = request.session.get('uname')

        if not uname:
            return render(
                request,
                'CompanyLogin.html',
                {'data': 'Session expired. Please login again.'}
            )

        description = request.POST.get('t1')
        salary = request.POST.get('t2')
        apply_date = request.POST.get('t3')
        skills = ','.join(request.POST.getlist('t4'))
        post_date = str(date.today())

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )

        with con:
            cur = con.cursor()
            cur.execute("SELECT MAX(job_id) FROM jobs")
            row = cur.fetchone()
            job_id = str(row[0] + 1) if row and row[0] else "1"

            cur.execute(
                "INSERT INTO jobs VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (job_id, uname, description, salary, post_date, apply_date, skills)
            )
            con.commit()

        context = {
            'data': f'<font size=3 color=blue>Job details added successfully with JOB ID = {job_id}</font>'
        }
        return render(request, 'PostJob.html', context)


def UpdateProfile(request):
    if request.method == 'GET':
        uname = request.session.get('uname')

        if not uname:
            return render(request, 'StudentLogin.html',
                          {'data': 'Session expired. Please login again.'})

        index = 0
        con = pymysql.connect(
            host='127.0.0.1', port=3306,
            user='root', password='root',
            database='placement', charset='utf8'
        )

        with con:
            cur = con.cursor()
            cur.execute("SELECT student_name FROM profile WHERE student_name=%s", (uname,))
            if cur.fetchone():
                index = 1

        if index == 0:
            return render(request, 'UpdateProfile.html', {})
        else:
            return render(request, 'ModifyProfile.html', {})


def UpdateProfileAction(request):
    if request.method == 'POST':

        # ✅ FIX: GET USERNAME FROM SESSION
        uname = request.session.get('uname')

        if not uname:
            return render(
                request,
                'StudentLogin.html',
                {'data': 'Session expired. Please login again.'}
            )

        qualification = request.POST.get('t1', False)
        percentage = request.POST.get('t2', False)
        passout = request.POST.get('t3', False)
        experience = request.POST.get('t4', False)

        myfile = request.FILES['t5'].read()
        fname = request.FILES['t5'].name

        skills = request.POST.getlist('t6')
        skills = ','.join(skills)

        db_connection = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',
            charset='utf8'
        )
        db_cursor = db_connection.cursor()

        student_sql_query = (
            "INSERT INTO profile VALUES("
            "'"+uname+"','"+qualification+"','"+percentage+"','"
            +passout+"','"+experience+"','"+fname+"','"+skills+"','0')"
        )

        db_cursor.execute(student_sql_query)
        db_connection.commit()

        # ✅ SAVE RESUME FILE
        resume_path = "PlacementApp/static/resumes/" + fname
        if os.path.exists(resume_path):
            os.remove(resume_path)

        with open(resume_path, "wb") as file:
            file.write(myfile)

        print(db_cursor.rowcount, "Record Inserted")

        if db_cursor.rowcount == 1:
            status = "<font size=3 color=blue>Profile successfully Updated</font>"
        else:
            status = "<font size=3 color=blue>error in updating profile</font>"

        context = {'data': status}
        return render(request, 'StudentScreen.html', context)

def ModifyProfileAction(request):
    if request.method == 'POST':
        uname = request.session.get('uname')

        if not uname:
            return render(
                request,
                'StudentLogin.html',
                {'data': 'Session expired. Please login again.'}
            )

        experience = request.POST.get('t1')
        skills = ','.join(request.POST.getlist('t3'))

        file = request.FILES['t2']
        fname = file.name

        con = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='root',
            database='placement',   # ✅ NOT job
            charset='utf8'
        )
        cur = con.cursor()

        cur.execute("""
            UPDATE profile
            SET experience=%s, resume=%s, skills=%s
            WHERE student_name=%s
        """, (experience, fname, skills, uname))

        con.commit()

        # Save resume safely (Windows-friendly)
        path = "PlacementApp/static/resumes/" + fname
        try:
            with open(path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)
        except PermissionError:
            pass

        return render(
            request,
            'StudentScreen.html',
            {'data': '<font size=3 color=blue>Profile successfully updated</font>'}
        )




                      
