from flask_wtf import Form
from wtforms import TextField
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms import IntegerField
from wtforms import HiddenField

from application.modules.nodes.models import CustomFields
from wtforms.validators import DataRequired

from application import db

from application.modules.nodes.models import Node, NodeType, NodeProperties


class NodeTypeForm(Form):
    name = TextField('Name', validators=[DataRequired()])
    url = TextField('Url', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    is_extended = BooleanField('Is extended')


def get_node_form(node_type):
    node_type = NodeType.query.filter_by(url=node_type).first()
    class ProceduralForm(Form):
        pass

    setattr(ProceduralForm,
        'name',
        TextField('Name', validators=[DataRequired()]))
    setattr(ProceduralForm,
        'url',
        TextField('Url'))
    setattr(ProceduralForm,
        'description',
        TextAreaField('Description', validators=[DataRequired()]))
    setattr(ProceduralForm,
        'node_type_id',
        HiddenField(default=node_type.id))

    for custom_field in CustomFields.query\
        .join(NodeType)\
        .filter(NodeType.url == node_type.url):
        
        if custom_field.field_type == 'text':
            field_properties = TextAreaField(custom_field.name, 
                validators=[DataRequired()])
        elif custom_field.field_type == 'string':
            field_properties = TextField(custom_field.name, 
                validators=[DataRequired()])
        elif custom_field.field_type == 'integer':
            field_properties = IntegerField(custom_field.name, 
                validators=[DataRequired()])
        elif custom_field.field_type == 'select':
            options = Node.query\
                .join(NodeType)\
                .filter(NodeType.url==custom_field.name_url)\
                .all()
            field_properties = SelectField(custom_field.name, 
                coerce=int,
                choices=[(option.id, option.name) for option in options] )
        
        setattr(ProceduralForm, custom_field.name_url, field_properties)

    return ProceduralForm()


def process_node_form(form, node_id=None):
    """Generic function used to process new nodes, as well as edits
    """
    if form.validate_on_submit():
        node_type = NodeType.query.get(form.node_type_id.data)
        if node_id:
            node = Node.query.get(node_id)
            node.name = form.name.data
            node.description = form.description.data
        else:
            node = Node(
                name=form.name.data,
                description=form.description.data,
                node_type_id=form.node_type_id.data)
            db.session.add(node)
        db.session.commit()

        for custom_field in CustomFields.query\
            .join(NodeType)\
            .filter(NodeType.url == node_type.url):

            for field in form:
                if field.name == custom_field.name_url:
                    if node_id:
                        # Query for the indivitual property
                        # TODO: collect all properties and loop through them
                        node_property = NodeProperties.query\
                            .filter_by(node_id=node_id)\
                            .filter_by(custom_field_id=custom_field.id)\
                            .first()
                        if node_property:
                            # Update the value of the property
                            node_property.value = field.data
                        else:
                            # If the property is missing we add it
                            node_property = NodeProperties(
                                node_id=node.id,
                                custom_field_id=custom_field.id,
                                value=field.data)
                            db.session.add(node_property)
                    else:
                        node_property = NodeProperties(
                            node_id=node.id,
                            custom_field_id=custom_field.id,
                            value=field.data)
                        db.session.add(node_property)
                    db.session.commit()
        return True
    else:
        return False
