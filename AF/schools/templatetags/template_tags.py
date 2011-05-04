from schools.models import *
from schools.forms import *
from django import template
from django.http import HttpResponse
from django.shortcuts import render_to_response
register = template.Library()


@register.filter  
def KLPrange(value):  
    return range(value)

        
@register.filter(name='displayValue')        
def displayValue(dictionary, key):
    try:
        return dictionary[key]
    except:
        pass     
        
@register.filter(name='assesmentUpdation')        
def assesmentUpdation(dictionary, key):
    try:
        return dictionary[key+'_u']
    except:
        pass                
        
@register.inclusion_tag("render_field.html")
def render_field(field,attributes=''):

    """ render a field with its errors, optionally passing in 

        attributes eg.:  

        {% render_field form.name "cols=40,rows=5,class=text,tabindex=2" %}



        this is equivalent to

        <p>{{form.name.errors}}</p>

        {{ form.name }}



        but will also add the custom attributes

    """

    return {'errors':field.errors,'widget':make_widget(field,attributes)}
    
def make_widget(field,attributes):

    attr = {}

    if attributes:

        attrs = attributes.split(",")

        if attrs:

            for at in attrs:

                key,value = at.split("=")

                attr[key] = value

    return field.as_widget(attrs=attr)

import datetime
from django import  forms

class DateDropdownWidget(forms.MultiWidget):
    def __init__(self,attrs=None,year_range=None,month_range=None,day_range=None):
        YEARS = year_range or range(2000,2021)
        MONTHES = month_range or range(1,13)
        DAYS = day_range or range(1,32)

        years = map( lambda x: (x,x), YEARS )
        months = map(lambda x:(x,x), MONTHES )
        days = map( lambda x: (x,x), DAYS )

        widgets = (
                forms.Select(choices=years),
                forms.Select(choices=months),
                forms.Select(choices=days),
                )
       
        super(DateDropdownWidget, self).__init__(widgets, attrs)
 
    def format_output(self,widgets):
        format = "<div>Year&nbsp;Month&nbsp;Day <span>%s&nbsp;</span><span>%s</span>&nbsp;%s&nbsp;</div>".decode('utf-8')
       
        return format%(widgets[0],widgets[1],widgets[2])

    def decompress(self,value):
      
        if value:
            return [value.year, value.month,value.day]
        return [None,None,None]

class DateField(forms.MultiValueField):
    widget = DateDropdownWidget
    def __init__(self,*args,**kwargs):
        fields = (
                forms.IntegerField( required=True),
                forms.IntegerField( required=True),
                forms.IntegerField( required=True ),
                )
        super(DateField, self).__init__(fields, *args,**kwargs )

    def compress(self,data_list):
        EMPTY_VALUES = [None, '']
        ERROR_EMPTY = "Fill the fields."
        ERROR_INVALID = "Enter a valid date."
      
        if data_list:
            if filter(lambda x: x in EMPTY_VALUES, data_list):
                raise forms.ValidationError(ERROR_EMPTY)
           
            try:
                return datetime.datetime(*map(lambda x:int(x),data_list))
            except ValueError:
                raise forms.ValidationError(ERROR_INVALID)
        return None


