""" AnswerApi file is used to store answers entered by data entry operators And also do validation while double entry"""

from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django_restapi.resource import Resource
from django_restapi.model_resource import Collection, Entry
from django_restapi.responder import *
from django_restapi.receiver import *
from AkshararestApi.BoundaryApi import ChoiceEntry
from django.template import Template, Context, RequestContext
from schools.forms import *
from schools.models import *
from django_restapi.authentication import *

from schools.signals import check_perm
from schools.receivers import KLP_obj_Perm
         
def KLP_DataEnry(request):
        return HttpResponse(KLP_ChangeAns(permitted_methods=('POST','GET')).read(request))
        
        
class KLP_ChangeAns(Resource):
    """ To Create and Edit Answers answer/data/entry/"""
    def read(self,request):
    	user = request.user # get Logged in user
        student =  request.POST.get('student')    #  get Student 
        programId = request.POST.get('programId') #  get programme id
        assessmentId = request.POST.get('assessmentId') # get Assessment Id
        student_groupId = request.POST.get('student_groupId') #  get Student group id
        studentObj = Student.objects.filter(pk=student).defer("child")[0]   # get student Object based on id
        Questions_list = Question.objects.filter(assessment__id=assessmentId).defer("assessment")  # get questions under assessment
        student_groupObj = StudentGroup.objects.filter(pk = student_groupId).values("institution")[0]  # get SG Object based on id
        assessmentObj = Assessment.objects.filter(pk=assessmentId).defer("programme")[0]  # get assessment Object based on id
        instObj = Institution.objects.filter(pk=student_groupObj["institution"]).defer("boundary")[0]  # get Institution Object based on id
        #Checking user permission based on institution and assessment
        check_perm.send(sender=None, user=user, instance=instObj, Assessment=assessmentObj, permission='Acess')
        check_perm.connect(KLP_obj_Perm)
        for question in Questions_list:
        	textField = 'student_%s_%s' %(student, question.id)        	
        	textFieldVal = request.POST.get(textField)  # get each text field values
        	try:
        		# If answer object already exists update data.
        		ansObj = Answer.objects.filter(question = question, student = studentObj).defer("question", "student")[0]
        		if textFieldVal:
        			if textFieldVal.lower() == 'ab':
        				# If text field value is ab(absent) then change answerGrade and answerScore to none and status to -99999
        				ansObj.answerGrade = None
        				ansObj.answerScore = None
        				ansObj.status = -99999
        			elif textFieldVal.lower() == 'uk':
        				# If text field value is uk(unknown) then change answerGrade and answerScore to none and status to -1
        				ansObj.answerGrade = None
        				ansObj.answerScore = None
        				ansObj.status = -1
        			elif question.questionType == 2:
        				# else question type is 2(Grade) then change status to none and store textfield value in answerGrade
        				ansObj.status = None
        				ansObj.answerGrade = textFieldVal
        			else:
        				# else question type is 1(Marks) then change status to none and store textfield value in answerScore
        				ansObj.status = None	
        				ansObj.answerScore = textFieldVal
        			if ansObj.doubleEntry == 1 and ansObj.user1 == user:
        				# if the doubleEntry value for answer is 1(only first user enter data) and user1 is same as logged in user change lastmodifiedBy to current user
					ansObj.lastmodifiedBy = user
				else:
					# else update doubleEntry to 2(second user also submits data), lastmodifiedBy and user2 to logged user
					ansObj.doubleEntry = 2
					ansObj.lastmodifiedBy = user
				       	ansObj.user2 = user
        			ansObj.save()	# Save Answer object
        	except :
        		if textFieldVal:
        			# If Answer object not exists create new answer object
				ansObj = Answer(question=question, student=studentObj, doubleEntry=1)
				ansObj.save()
				if textFieldVal.lower() == 'ab':
					# If text field value is ab(absent) then set status to -99999
					ansObj.status = -99999
				elif textFieldVal.lower() == 'uk':
					# If text field value is uk(unknown) then set status to -1
					ansObj.status = -1
				elif question.questionType == 2:
					# else if  question type is 2(Grade) then store textfield value in answerGrade
        				ansObj.answerGrade = textFieldVal
        			else:
        				# else if  question type is 1(Marks) then store textfield value in answerScore
        				ansObj.answerScore = textFieldVal
        			ansObj.lastmodifiedBy = user	# set last modified by and user1 to logged in user 
        			ansObj.user1 = user
        			ansObj.save()
	        
	return "Data Saved"


def KLP_DataValidation(request):
    """ To Validate data for Doble Entry answer/data/validation/"""
    validateId = request.POST.get('validateField')  #  Get ValidateId (student and question id)
    validateValue = request.POST.get('validateValue')  #  Get Text field value to validate
    listIds = validateId.split('_')   
    # Query Answer object based on student and question id
    ansObj = Answer.objects.filter(student__id=listIds[1], question__id=listIds[2]).defer("student","user1", "user2", "lastmodifiedBy")[0]    
    respStr = False
    dEntry = int(ansObj.doubleEntry)  # reads dE value
    if dEntry in [0,2]:
        # if dEntry in 0 0r 2 return true
    	respStr = True
    else:
    	# else check text field value
    	if validateValue:    		
	    	if validateValue.lower() == 'ab':
	    		# If text field value is ab(absent) and answer status is -99999 then return true
	    		if ansObj.status == -99999:
	    			respStr = True
	    	elif validateValue.lower() == 'uk':
	    		# If text field value is uk(unknown) and answer status is -1 then return true
	    		if ansObj.status == -1:
	    			respStr = True
	    	elif ansObj.question.questionType == 2:	    	
	    	    try:
	    	    	    # If question type is 2(Grade) then match with answer grade if matches return true
		    	    if ansObj.answerGrade.lower() == validateValue.lower():
		    	        respStr = True
		    	    elif float(ansObj.answerGrade) == float(validateValue):
		    	    	respStr = True
		    except:
		    	pass
	    	else:
	    	    try:
	    	    	    # If question type is 1(marks) then match with answer score if matches return true
		    	    if float(ansObj.answerScore) == float(validateValue):
		    	        respStr = True
	    	    except:
	    	    	pass
	else:
		respStr = False
    return HttpResponse(simplejson.dumps(respStr))

        
urlpatterns = patterns('', 
   url(r'^answer/data/entry/$', KLP_DataEnry),
   url(r'^answer/data/validation/$', KLP_DataValidation),
)        
