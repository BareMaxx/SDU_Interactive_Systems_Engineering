from flask import jsonify, Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import exists
from sqlalchemy.orm import joinedload
from wtforms.validators import ValidationError


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yoink.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    # Implement a function to get the user object based on user_id
    return User(user_id)

followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    yoinks = db.relationship('Yoink', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    profile_picture = db.Column(db.String(255))  # Example for a profile picture (store file path or URL)
    bio = db.Column(db.String(250))  # Adjust the length as needed
    # New fields for followers/following
    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.get('id')).count() > 0

class Yoink(db.Model):
    __tablename__ = 'yoink'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(280), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates='yoinks')
    likes = db.relationship('Like', backref='liked_yoink')
    comments = db.relationship('Comment', backref='yoink', lazy=True)

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(280), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    yoink_id = db.Column(db.Integer, db.ForeignKey('yoink.id'))

class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    yoink_id = db.Column(db.Integer, db.ForeignKey('yoink.id'), nullable=False)

    # Define the relationship with the Yoink model using a different backref name
    yoink = db.relationship('Yoink', back_populates='likes')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    repeat_password = PasswordField('Repeat Password', validators=[DataRequired()])

    def validate_repeat_password(self, field):
        if self.password.data != field.data:
            raise ValidationError('Passwords must match.')

    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class YoinkForm(FlaskForm):
    content = TextAreaField('Your Yoink', validators=[DataRequired()])
    submit = SubmitField('Yoink It')

@app.route('/', methods=['GET', 'POST'])
def home():
    hide_navigation  = True  # Set hide_navigation  to True for the welcome page

    if current_user.is_authenticated:
        # User is logged in
        form = YoinkForm()
        if form.validate_on_submit():
            content = form.content.data
            user_id = current_user.id
            create_yoink(content, user_id)
            flash('Yoink posted', 'success')
            return redirect(url_for('home'))

        if request.method == 'GET':
            yoinks, yoink_likes = get_yoinks()
            hide_navigation = False  # Set hide_navigation  to False for the authenticated home page
            return render_template('home_authenticated.html', form=form, yoinks=yoinks, yoink_is_liked_by_user=yoink_is_liked_by_user, yoink_likes=yoink_likes, hide_navigation=hide_navigation )

    # User is not logged in
    return render_template('home_welcome.html', hide_navigation =hide_navigation )

# Define the create_user function
def create_user(username, email, password):
    # Logic to create a new user and add it to the database
    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)  # Automatically log in the newly registered user
    return new_user  # Return the new_user to allow logging in

# Your route handling the registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form = RegistrationForm()

        if form.validate_on_submit():
            new_user = create_user(form.username.data, form.email.data, form.password.data)
            flash('Account created successfully', 'success')
            return jsonify({'success': True, 'message': 'Account created successfully'})

        errors = {field.name: field.errors for field in form if field.errors}
        return jsonify({'success': False, 'errors': errors})

    # Handle the GET request (render the registration form)
    form = RegistrationForm()
    return render_template('register.html', form=form, hide_navigation=True)


def authenticate_user(email, password):
    # Check if the user with the provided email exists
    user = User.query.filter_by(email=email).first()

    if user and user.password == password:
        # If the user exists and the password matches, return the user's ID
        return user

    # If the user doesn't exist or the password is incorrect, return None
    return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET'])
def show_login():
    form = LoginForm()
    return render_template('login.html', form=form, hide_navigation=True)

@app.route('/login', methods=['POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Authenticate the user by their credentials, return user if successful
        user = authenticate_user(email, password)

        if user:
            login_user(user)
            flash('Login successful', 'success')
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            flash('Invalid email or password', 'error')
            return jsonify({'success': False, 'message': 'Invalid email or password'})

    # Return an error response if the form is not valid
    return jsonify({'success': False, 'message': 'Invalid form submission'})


# Logout route
@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for('home'))  # Redirect to your home or any appropriate route after logging out

@app.route('/like/<int:yoink_id>', methods=['POST', 'DELETE'])
def like(yoink_id):
    if request.method == 'POST' and current_user.is_authenticated:
        user_id = current_user.id

        user = User.query.get(user_id)
        yoink = Yoink.query.get(yoink_id)

        if user and yoink:
            like_exists = db.session.query(exists().where(
                (Like.yoink_id == yoink.id) & (Like.user_id == user.id)
            )).scalar()

            if like_exists:
                # If the user has already liked the yoink post, unlike it
                Like.query.filter_by(yoink_id=yoink.id, user_id=user.id).delete()
            else:
                # If the user has not liked the yoink post, like it
                like = Like(user_id=user.id, yoink_id=yoink.id)
                db.session.add(like)

            db.session.commit()

            # Get the updated like count
            updated_like_count = Like.query.filter_by(yoink_id=yoink.id).count()

            # Respond with JSON containing the updated like count
            return jsonify({'likes': updated_like_count})

    elif request.method == 'DELETE' and current_user.is_authenticated:
        # Handle the case when the user wants to "unlike" the post
        user_id = current_user.id
        yoink = Yoink.query.get(yoink_id)

        if user_id and yoink:
            like_exists = db.session.query(exists().where(
                (Like.yoink_id == yoink.id) & (Like.user_id == user_id)
            )).scalar()

            if like_exists:
                # If the user has already liked the yoink post, unlike it
                Like.query.filter_by(yoink_id=yoink.id, user_id=user_id).delete()
                db.session.commit()

                # Get the updated like count
                updated_like_count = Like.query.filter_by(yoink_id=yoink.id).count()

                # Respond with JSON containing the updated like count
                return jsonify({'likes': updated_like_count})


    return redirect(url_for('home'))
    
@app.route('/comment/<int:yoink_id>', methods=['GET', 'POST'])
def comment(yoink_id):
    # Logic for handling comments on a specific yoink with ID 'yoink_id'
    # You may perform actions such as fetching comments, adding comments, etc.
    return redirect(url_for('home'))  # Redirect to home or an appropriate route after comment action

@app.route('/add_comment/<int:yoink_id>', methods=['POST'])
def add_comment(yoink_id):
    if current_user.is_authenticated:
        # Get the comment text from the form data
        comment_text = request.form.get('comment_text')
        
        # Save the comment to the database for the corresponding yoink post
        if comment_text:
            new_comment = Comment(text=comment_text, user_id=current_user.id, yoink_id=yoink_id)
            db.session.add(new_comment)
            db.session.commit()

    return redirect(url_for('home'))

@app.route('/comments/<int:yoink_id>', methods=['GET'])
def view_comments(yoink_id):
    yoink = Yoink.query.get(yoink_id)
    comments = Comment.query.filter_by(yoink_id=yoink_id).all()
    return render_template('comments.html', yoink=yoink, comments=comments)

@app.route('/profile/<int:user_id>')
def profile(user_id):
    if current_user.is_authenticated:
        user = User.query.get(user_id)
        
        # Fetch the user's details
        user_profile = {
            'id': user.id,
            'username': user.username,
            'profile_picture': user.profile_picture,  # Assuming the user has a profile picture attribute
            'bio': user.bio  # Assuming the user has a bio attribute
        }
        
        # Fetch the user's yoinks
        user_yoinks = Yoink.query.filter_by(user_id=user.id).all()
        
        # Fetch the user's comments on yoinks
        user_comments = Comment.query.filter_by(user_id=user.id).all()
        
        # Fetch the yoinks liked by the user
        liked_yoinks = []
        likes = Like.query.filter_by(user_id=user.id).all()
        for like in likes:
            liked_yoinks.append(Yoink.query.get(like.yoink_id))
        
        return render_template('profile.html', user=user_profile, yoinks=user_yoinks, comments=user_comments, liked_yoinks=liked_yoinks)
    else:
        # Redirect to the login page if the user is not authenticated
        return redirect(url_for('login'))

@app.route('/follow/<int:followed_id>', methods=['POST'])
@login_required  # This decorator ensures the user is logged in
def follow_user(followed_id):
    followed_user = User.query.get(followed_id)
    if followed_user:
        current_user.followed.append(followed_user)
        db.session.commit()
    return redirect(url_for('profile', user_id=followed_id))  # Redirect to the user's profile

@app.route('/unfollow/<int:followed_id>', methods=['POST'])
@login_required  # This decorator ensures the user is logged in
def unfollow_user(followed_id):
    followed_user = User.query.get(followed_id)
    if followed_user and followed_user in current_user.followed:
        current_user.followed.remove(followed_user)
        db.session.commit()
    return redirect(url_for('profile', user_id=followed_id))  # Redirect to the user's profile

# Function to create a yoink and add it to the database
def create_yoink(content, user_id):
    with app.app_context():
        new_yoink = Yoink(content=content, user_id=user_id)
        db.session.add(new_yoink)
        db.session.commit()

# Function to get yoinks from the database
def get_yoinks():
    with app.app_context():
        # Fetching Yoinks with related User information eagerly loaded
        yoinks = db.session.query(Yoink).options(joinedload(Yoink.user)).all()
        yoink_likes = {yoink.id: len(yoink.likes) for yoink in yoinks}
        return yoinks, yoink_likes

def yoink_is_liked_by_user(yoink_id):
    # This function should check if the current user has liked the yoink with the given ID
    # You'll need to implement the query based on your database model and the relationship between users and liked yoinks
    with app.app_context():
        # For example, assuming you have a current_user variable accessible
        liked_yoink = Like.query.filter_by(user_id=current_user.id, yoink_id=yoink_id).first()
        return liked_yoink is not None

# Follow a user
def follow_user(user_id, followed_id):
    user = User.query.filter_by(id=user_id).first()
    followed = User.query.filter_by(id=followed_id).first()
    if user and followed:
        user.followed.append(followed)
        db.session.commit()

# Unfollow a user
def unfollow_user(user_id, followed_id):
    user = User.query.filter_by(id=user_id).first()
    followed = User.query.filter_by(id=followed_id).first()
    if user and followed:
        user.followed.remove(followed)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()
        db.create_all()
    app.run(debug=True)
