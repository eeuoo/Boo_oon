from flask import Flask, url_for, render_template, request, Response, session, jsonify, make_response, redirect, flash, json, g
from boo.db_class import Users, Cmt, Lists, Follow, Ranking, Likecnt, DM, db_session
from datetime import date, datetime, timedelta
from werkzeug import generate_password_hash, check_password_hash
from sqlalchemy import update
from sqlalchemy.orm import relationship, backref, joinedload
from flask_socketio import SocketIO, emit, send
import os
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.debug = True

app.config.update(
	SECRET_KEY='X1243yRH!mMwf',
	SESSION_COOKIE_NAME='pyweb_flask_session',
	PERMANENT_SESSION_LIFETIME=timedelta(31)      # 31 days
)

islogin = False
user = ''


# 메인페이지
@app.route('/boo', methods=['GET','POST'])
def main():
    global islogin, user

    session['islogin'] = islogin
    islogin = session.get('islogin')

    if islogin == False :
        user = ''
    elif user != "" :
        user = session.get('loginUser')['username']

    u = Users.query.filter(Users.username == user).first()
    
    return render_template('boo_main.html', islogin=islogin, user = user, userinfo=u)


# 서브페이지
@app.route('/boo/sub')
def sub():
    global islogin, user

    session['islogin'] = islogin
    islogin = session.get('islogin')

    if islogin == False :
        user = ''
    elif user != "" :
        user = session.get('loginUser')['username']

    return render_template('boo_sub.html', islogin=islogin, user=user)


# 마이페이지
@app.route('/boo/mypage/<user_name>')
def mypage(user_name):
    global islogin, user

    isfollow = False
    my_follow_list = []
    mydata = {}

    if islogin == False :
        user = ''
    elif user != "" :
        user = session.get('loginUser')['username']
        my = Users.query.filter(Users.username == user).first()
        mydata = my.json()
        my_follow_list = [ ff.userno for ff in Follow.query.filter(Follow.following == my.userno).all() ]
        
    u = Users.query.filter(Users.username == user_name).first()
   
    if u.userno in my_follow_list :
        isfollow = True
    
    host_follow_list = Follow.query.filter(Follow.following == u.userno).all()
    follow = [ Users.query.filter(Users.userno == f.userno).first().json() for f in host_follow_list]

    host_follower_list = Follow.query.filter(Follow.userno == u.userno).all()
    follower = [ Users.query.filter(Users.userno == f.following).first().json() for f in host_follower_list ] 
    
    return render_template('mypage.html', host=u, user=user, isfollow = isfollow, followlist=follow, followerlist=follower, userinfo=mydata)

# 채팅페이지
@app.route('/boo/chat')
def chat():
    global islogin, user

    session['islogin'] = islogin
    islogin = session.get('islogin')

    if islogin == False :
        user = ''
    elif user != "" :
        user = session.get('loginUser')['username']

    return render_template('boo_chat.html', islogin=islogin, user=user)


# 가입시 아이디, 이메일 중복 체크.
@app.route('/boo/idcheck', methods=['GET','POST'])
def ifexists():
    username = request.form.get('username')

    checkid = Users.query.filter(Users.username == username).first()
    checkem = Users.query.filter(Users.email == username).first()
    
    if checkid == None and checkem == None :
        return jsonify(username='가입 가능')

    elif checkid == None and checkem != None : 
        return jsonify(username='이메일 있음')

    else : 
        return jsonify(username='이미 있음')


# 회원가입.
@app.route('/boo/regist', methods=['GET','POST'])
def regist_post():
    username = request.form.get('username')
    pw = request.form.get('pw')
    pw2 = request.form.get('pw2')
    birthyear = request.form.get('birthyear')
    birthmonth = request.form.get('birthmonth')
    birthday = request.form.get('birthday')
    birthdate = birthyear + getzero(birthmonth) + getzero(birthday)
    sidogun = request.form.get('sidogun')
    city = request.form.get('city')
    addr = sidogun + ' ' + city
    gender = request.form.get('gender')
    job = request.form.get('job')
    email = request.form.get('email')
    img = None

    u = Users(username, generate_password_hash(pw), birthdate, addr, gender, job, email, img)

    try:
        db_session.add(u)
        db_session.commit()

        flash("%s 님, 가입을 환영합니다!" % username)
        
    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    return redirect('/boo')
    

# 로그인.
@app.route('/boo/login', methods=['GET','POST'])
def login_post():
    global islogin, user

    username = request.form.get('username')
    pw = request.form.get('pw')

    u = Users.query.filter(Users.username == username).first()

    print('login의 첫번째 islogin >>>???>>>>', islogin)
    if u is not None:
    
        if check_password_hash(u.pw, pw) == True:

            islogin = True
            user = u.username

            session['loginUser'] = { 'username': u.username }

            return redirect("/boo")
            
        else:
            return jsonify(login='비밀번호 오류')

    else:  
        return jsonify(login='아이디 오류')  # if u is None
        print(">>>>>>>>>>>로그인 실패<<<<<<<<<<<<")  
        


# 로그아웃.
@app.route('/boo/logout')
def logout():
    
    global islogin

    if session.get('loginUser'):
        del session['loginUser']

        islogin = False

    return redirect('/boo')


# 글쓰기.
@app.route('/boo/write', methods=['POST'])
def write():
    global user

    list_title = request.form.get('list_title')
    list_txt = request.form.get('list_txt')
    public = request.form.get('public')
    (cmt_count, like_cnt, hate_cnt, list_date, isdelete) = (None, None, None, None, None)
    lid = request.form.get('editId')

    u = Users.query.filter(Users.username == user).first()
    
    lists = Lists( u.userno, list_title, list_txt, cmt_count, like_cnt, hate_cnt, public, list_date, isdelete)

    l = Lists.query.filter(Lists.list_id == lid).first()

    print('#########', 'lid====', lid)
    print('@@@@@@@@@', l)

    try:
        if l == None :
            db_session.add(lists)
            
        else :
            l.list_title = list_title
            l.list_txt = list_txt
            if public == 0 :
                l.public = 0
            else :  l.public = 1
            
        db_session.commit()
    
    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    return redirect('/boo')


# 카드 삭제
@app.route('/boo/delete', methods=['POST'])
def boo_delete():
    l_id = request.values.get('list_id')

    try:
        Cmt.query.filter(Cmt.list_id == l_id).delete()
        Lists.query.filter(Lists.list_id == l_id).delete()
        db_session.commit()

    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    return redirect('/boo')
    

# 뜬구름 좋아요, 싫어요 수 조정
@app.route('/boo/like_hate', methods=['GET', 'POST'])
def hate():
    l_id = request.values.get('list_id')
    num = request.values.get('num')
    feel = request.values.get('feel')

    lst = Lists.query.filter(Lists.list_id == l_id).first()

    try:
        if feel == 'like' :
            if num == 'add' :
                lst.likecnt += 1
            else :
                lst.likecnt -= 1

        elif feel == 'hate':
            if num == 'add' :
                lst.hatecnt -= 1
            else :
                lst.hatecnt += 1

        db_session.commit()

    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    return redirect('/boo')


### 댓글 ####
@app.route('/boo/comment', methods=['POST'])
def comment_post():
    global user
    u = Users.query.filter(Users.username == user).first()
    

    list_id = request.values.get('list_id')
    cmt_txt = request.values.get('cmt_txt')
    ( cmt_date, cmt_like, cmt_hate ) = (None, None, None)

    c = Cmt(u.userno, cmt_txt, cmt_date, list_id, cmt_like, cmt_hate)

    try:
        db_session.add(c)
        db_session.commit()
        
        
    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()

    return redirect('/boo')


@app.route('/boo/comment/<list_id>', methods=['GET'])
def comment_get(list_id):

    cmts = Cmt.query.filter(Cmt.list_id == list_id).order_by(Cmt.cmt_id.desc()).all()

    return jsonify([c.json() for c in cmts])


@app.route('/boo/comment/<cmt_id>', methods=['DELETE'])
def comment_delete(cmt_id):

    print("DDDDDDDDDDDDDDDDD>>>", cmt_id)

    try:
        Cmt.query.filter(Cmt.cmt_id == cmt_id).delete()
        db_session.commit()

    except SQLAlchemyError as err:
        db_session.rollback()
        print("Error!!", err)

    return jsonify({"result": 'OK'})


# 댓글 좋아요, 싫어요 수 조정
@app.route('/boo/cmt_like_hate/<list_id>', methods=['POST'])
def cmt_like(list_id):
    
    num = request.values.get('num')
    cmt_id = request.values.get('cmt_id')

    cmt = Cmt.query.filter('list_id=:list_id and cmt_id=:cmt_id').params(
        list_id=list_id, cmt_id=cmt_id).first()

    try:
       
        if num == 'add' :
            cmt.cmt_like += 1
        else :
            cmt.cmt_hate -= 1

        db_session.commit()

    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    return redirect('/boo')



# 카드 
@app.route('/boo/lists', methods=['GET'])
def cards():

    lists = Lists.query.order_by(Lists.list_id.desc())
    lists = lists.filter(Lists.public == 1).all()

    return jsonify( [l.json() for l in lists] )


# 마이페이지 카드
@app.route('/boo/mylist/<username>', methods=['GET'])
def get_mylist(username):
    u = Users.query.filter(Users.username == username).first()

    lists = Lists.query.filter(Lists.userno == u.userno).order_by(Lists.list_id.desc()).all()

    return jsonify( [l.json() for l in lists] , u.json() )



# 랭크
@app.route('/boo/rank', methods=['GET'])
def rank():

    lists = Lists.query.order_by(Lists.likecnt.desc())
    lists = lists.filter(Lists.public == 1).all()

    return jsonify( [l.json() for l in lists] )
    

# 팔로우
@app.route('/boo/follow', methods=['POST'])
def follow_post():

    username = request.values.get('user')
    following = request.values.get('following')

    host = Users.query.filter(Users.username == username).first()
    guest = Users.query.filter(Users.username == following).first()

    f = Follow(host.userno, guest.userno)

    try:
        db_session.add(f)
        db_session.commit()

    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    rd = 'boo/mypage/' + username
    return redirect(rd)

# 팔로우
@app.route('/boo/delfollow', methods=['POST'])
def follow_delete():

    username = request.values.get('user')
    following = request.values.get('following')

    host = Users.query.filter(Users.username == username).first()
    guest = Users.query.filter(Users.username == following).first()

    try:
        print('삭제삭제삭제삭제삭제삭제삭제삭제삭제삭제삭제삭제')
        Follow.query.filter(Follow.userno == host.userno, Follow.following == guest.userno).delete()
        db_session.commit()

    except Exception as err:
        print("Error on users>>>", err)
        db_session.rollback()
    
    rd = 'boo/mypage/' + username
    return redirect(rd)



# 프로필 사진 수정
@app.route('/boo/upload', methods=["POST"])
def upload():
    upfile = request.files['file']    
    username = request.form.get('username')
    print("mmmmmmmmmmmmmmmmmm>>", username, upfile.filename, upfile.filename.replace('..', ''))
    f = upfile.filename.replace('..', '')
    f = rename(f, username)

    path = os.path.join("./boo/static/img/upfiles", f )

    upfile.save(path)

    path = path[6:]

    print(path)

    u = Users.query.filter(Users.username ==  username).first()

    try:
        print('uuuuu', u)
        u.img = path
        db_session.merge(u)
        db_session.commit()
    
    except SQLAlchemyError as err:
        db_session.rollback()
        print("Error >>", err)

    return jsonify({"path": path})

@socket_io.on("message")
def request(message):
    print("message : "+ message)
    to_client = dict()
    
    if message == 'new_connect':
        to_client['message'] = "새로운 유저가 난입하였다!!"
        to_client['type'] = 'connect'
    else:
        to_client['message'] = message
        to_client['type'] = 'normal'
    # emit("response", {'data': message['data'], 'username': session['username']}, broadcast=True)
    send(to_client, broadcast=True)


############### teardown_appcontext #############################

@app.teardown_appcontext
def teardown_context(exception):
    print(">>> teardown context!!", exception)
    db_session.remove() 


############### 필요해서 만든 파이썬 함수 #############################

def getzero(md):
    if len(md) == 2 :
        return md
    else :
        return '0' + md


def rename(path, username):
    
    idx = path.rindex('.')  
    print('rename', idx, path)
    if idx == -1:
        path = username
        print('rename', idx, path)
    else:
        path = username + path[idx:]
        print('rename', idx, path)

    return path
    