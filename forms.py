from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class CaseForm(FlaskForm):
    title = StringField('Case Title', validators=[DataRequired()])
    description = TextAreaField('Case Description', validators=[DataRequired()])
    submit = SubmitField('Log Case')

from flask_wtf.file import FileField, FileAllowed

class DocumentUploadForm(FlaskForm):
    document = FileField('Upload Document', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Convert to PDF')
