from wtforms import BooleanField, DateTimeLocalField, Form, StringField, PasswordField, SubmitField, DateTimeField, FloatField, TextAreaField, IntegerRangeField
from wtforms.validators import DataRequired, Length, InputRequired

class LoginForm(Form):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4, max=64)])
    submit = SubmitField("Submit")