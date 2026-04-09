from wtforms import DateTimeLocalField, Form, StringField, PasswordField, SubmitField, TextAreaField, HiddenField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, EqualTo, ValidationError, Email
from enum import Enum

class Type(Enum):
    PROTEST = "protest"
    MEETING = "meeting"
    MARCH = "march"
    COMMUNITY_SUPPORT = "community_support"
    INCIDENT_REPORT = "incident_report"
    OTHER = "other"

class Category(Enum):
    FUEL = "fuel"
    COST_OF_LIVING = "cost_of_living"
    HOUSING = "housing"
    INTERNATIONAL = "international"
    PALESTINE = "palestine"
    SOCIAL = "social"
    ENVIRONMENTAL = "environmental"
    ECONOMIC = "economic"
    REPUBLICAN = "republican"
    ANTI_GOVERNMENT = "anti_government"
    POLITICAL = "political"
    OTHER = "other"

class LoginForm(Form):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4, max=64)])
    submit = SubmitField("Submit")

class RegistrationForm(Form):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=32)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=4, max=64)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")])
    email = StringField("Email (Optional)", validators=[Optional(), Email()])
    phone = StringField("Phone (Optional)", validators=[Optional(), Length(max=20)])
    submit = SubmitField("Create Account")

class AddEventForm(Form):
    name = StringField("Event Name", validators=[DataRequired(), Length(min=2, max=80)])
    description = TextAreaField("Description (Optional)", validators=[Optional(), Length(min=5, max=1200)])
    link = StringField("Link (Optional)", validators=[Optional(), Length(max=255)])
    contact = StringField("Contact (Optional)", validators=[Optional(), Length(max=120)])
    start_time = DateTimeLocalField("Start Time (Optional)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    end_time = DateTimeLocalField("End Time (Optional)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    event_type = SelectField(
        "Event Type",
        validators=[DataRequired()],
        choices=[(event_type.value, event_type.value.replace("_", " ").title()) for event_type in Type]
    )
    category = SelectField(
        "Category",
        validators=[DataRequired()],
        choices=[(category.value, category.value.replace("_", " ").title()) for category in Category]
    )
    latitude = HiddenField("Latitude", validators=[DataRequired()])
    longitude = HiddenField("Longitude", validators=[DataRequired()])
    submit = SubmitField("Add Event")


class SearchForm(Form):
    name = StringField("Name", validators=[Optional(), Length(max=80)])
    latitude = HiddenField("Latitude", validators=[Optional()])
    longitude = HiddenField("Longitude", validators=[Optional()])
    category = SelectField(
        "Category",
        validators=[Optional()],
        choices=[("all", "All Categories")] + [(category.value, category.value.replace("_", " ").title()) for category in Category],
    )
    event_type = SelectField(
        "Type",
        validators=[Optional()],
        choices=[("all", "All Types")] + [(event_type.value, event_type.value.replace("_", " ").title()) for event_type in Type],
    )
    start_time = DateTimeLocalField("Start Time", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    end_time = DateTimeLocalField("End Time", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    radius_km = IntegerField("Radius", validators=[Optional()])
    submit = SubmitField("Search")