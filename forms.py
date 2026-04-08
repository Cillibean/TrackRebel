from wtforms import DateTimeLocalField, Form, StringField, PasswordField, SubmitField, TextAreaField, HiddenField, SelectField
from wtforms.validators import DataRequired, Length, Optional

class LoginForm(Form):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4, max=64)])
    submit = SubmitField("Submit")

class AddEventForm(Form):
    name = StringField("Event Name", validators=[DataRequired(), Length(min=2, max=80)])
    description = TextAreaField("Description (Optional)", validators=[Optional(), Length(min=5, max=1200)])
    start_time = DateTimeLocalField("Start Time (Optional)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    end_time = DateTimeLocalField("End Time (Optional)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    event_type = SelectField(
        "Event Type",
        validators=[DataRequired()],
        choices=[
            ("protest", "Protest"),
            ("meeting", "Meeting"),
            ("march", "March"),
            ("community", "Community Support"),
            ("incident", "Incident Report"),
            ("other", "Other")
        ]
    )
    latitude = HiddenField("Latitude", validators=[DataRequired()])
    longitude = HiddenField("Longitude", validators=[DataRequired()])
    submit = SubmitField("Add Event")