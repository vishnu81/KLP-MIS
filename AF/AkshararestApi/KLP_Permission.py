"""
KLP_Permission file is used 
1) To assign permissions
2) To list users
3) To Delete users
4) To show permissions at diffrent level of boundaries
5) To revoke user permissions
6) To reassign permissions to user.
"""
from django.conf.urls.defaults import *
from django.shortcuts import render_to_response
from django_restapi.resource import Resource
from schools.models import *
from schools.forms import *
from django_restapi.model_resource import Collection, Entry
from django_restapi.responder import *
from django_restapi.receiver import *
from AkshararestApi.BoundaryApi import ChoiceEntry
from django.template import RequestContext
from django.contrib.auth.models import User
from django.utils import simplejson
from django.db.models import Q	

from schools.signals import check_user_perm
from schools.receivers import KLP_user_Perm

def KLP_Assign_Permissions(request):
	""" This method is used to assign permissions"""
	""" Check logged in user permissions to assign permissions"""
	check_user_perm.send(sender=None, user=request.user, model='Users', operation=None)
        check_user_perm.connect(KLP_user_Perm)
	respDict = {}
	# get selected users list to assign permissions
	deUserList = request.POST.getlist('assignToUser')
	#get selected permissions list
	permissions = request.POST.getlist('userPermission')
	# get permission type
	permissionType = request.POST.get('permissionType')
	# get assessment Id to assign assessment permissions
	assessmentId = request.POST.get('assessmentId')
	# get boundary category 
	bound_cat = request.POST.get('bound_cat')
	# get selected institutions list
	inst_list = request.POST.getlist('instName')
	# get selected boundaries list
	bound_list = request.POST.getlist('boundaryName')
	# get assessment permission (True or False)
	assessmentPerm = request.POST.get('assessmentPerm')
	count, asmCount, assignedAsmIds = 0, 0, []
	if not deUserList:
		# If no users selected respond back with error message (Select Atleast One User)
		respDict['respMsg'] = 'Select Atleast One User'
		respDict['isSuccess'] = False
	elif not permissions:
		# if permissions not selected respond back with error message (Select Atleast One Permission)
		respDict['respMsg'] = 'Select Atleast One Permission'
		respDict['isSuccess'] = False
	elif bound_cat in ['district', 'block', 'project']:
		# if bound category in 'district', 'block', 'project' check for boundary list
		if not bound_list:
			# if boundary list is empty respond back with error message (Select Atleast One Boundary)
			respDict['respMsg'] = 'Select Atleast One Boundary'
			respDict['isSuccess'] = False
		else:
			if bound_cat == 'district':
				# if boundary category is district query for institutions under sub boundaries
				for bound in bound_list:
					inst_list = Institution.objects.filter(boundary__parent__id = bound, active=2).values_list('id', flat=True).distinct()
					# get count of institutions to show count of assigned institution objects to user
					count = count + inst_list.count()
					# call assignPermission method to assign permissions
					asmIdList = assignPermission(inst_list, deUserList, permissions, permissionType, assessmentId, assessmentPerm)
					assignedAsmIds.extend(asmIdList)
			elif bound_cat in [ 'block', 'project']:
				# if boundary category is district query for institutions under sub boundaries
				for bound in bound_list:
					inst_list = Institution.objects.filter(boundary__id = bound, active=2).values_list('id', flat=True).distinct() 
					# get count of institutions to show count of assigned institution objects to user
					count = count + inst_list.count()
					# call assignPermission method to assign permissions
					asmIdList = assignPermission(inst_list, deUserList, permissions, permissionType, assessmentId, assessmentPerm)
					assignedAsmIds.extend(asmIdList)
			if assessmentPerm:
				assignedAsmIds =  list(set(assignedAsmIds))
				# get length of assessment ids to show count of assigned assessment objects to user
				asmCount = len(assignedAsmIds)				
				respDict['respMsg'] = 'Assigned Permissions successfully for %s Institutions  and %s Assessments Assigned successfully' %(count, asmCount)
			else:
				respDict['respMsg'] = 'Assigned Permissions successfully for %s Institutions' %(count)
			respDict['isSuccess'] = True
		
	else:
		# if bound category in 'cluste' or 'circle' check for institution list
		if not inst_list:
			# if institutions list is empty  respond back with error message (Select Atleast One Institution)
			respDict['respMsg'] = 'Select Atleast One Institution'
			respDict['isSuccess'] = False				
		else:
			# get count of institutions to show count of assigned institution objects to user
			count = count + len(inst_list)
			# call assignPermission method to assign permissions
			asmIdList = assignPermission(inst_list, deUserList, permissions, permissionType, assessmentId, assessmentPerm)
			assignedAsmIds.extend(asmIdList)
			if assessmentPerm:
				assignedAsmIds =  list(set(assignedAsmIds))
				# get length of assessment ids to show count of assigned assessment objects to user
				asmCount = len(assignedAsmIds)
				respDict['respMsg'] = 'Assigned Permissions successfully for  %s Institutions and %s Assessments Assigned successfully' %(count, asmCount)
			else:
				respDict['respMsg'] = 'Assigned Permissions successfully for  %s Institutions' %(count)
			respDict['isSuccess'] = True
	if count == 0:
		respDict['respMsg'] = 'No Institutions Found to Assign Permissions'
		respDict['isSuccess'] = False		
	
	return HttpResponse(simplejson.dumps(respDict), content_type='application/json; charset=utf-8')	
	
def assignPermission(inst_list, deUserList, permissions, permissionType, assessmentId=None, assessmentPerm=None):
	assignedAsmIds = []
	for inst_id in inst_list:
		# get Institution object using id
		instObj = Institution.objects.get(pk=inst_id)
		for deUser in deUserList:
			# get user object
			userObj = User.objects.get(id=deUser)
			if permissionType == 'permissions':
				# if permission type is permissions set institution level permissions for the user
				userObj.set_perms(permissions, instObj)
				if assessmentPerm:
					# if assessmentPerm is true assign assessment also to the user.
					sg_list = StudentGroup.objects.filter(institution__id=inst_id).values_list('id', flat=True).distinct()
					asmIds = Assessment_StudentGroup_Association.objects.filter(student_group__id__in= sg_list, active=2).values_list("assessment__id", flat=True).distinct()
					for asmId in asmIds:
						assessmentObj = Assessment.objects.get(id=asmId)
						try:
							permObj = UserAssessmentPermissions.objects.get(user = userObj, instituion = instObj, assessment = assessmentObj)
							permObj.access = True
							permObj.save()							
						except:
							permObj = UserAssessmentPermissions(user = userObj, instituion = instObj, assessment = assessmentObj, access=True)
							permObj.save()
							
					assignedAsmIds.extend(asmIds)
			else:
				# else assign assessment permissions to user.
				assessmentObj = Assessment.objects.get(pk=assessmentId)
				try:
					permObj = UserAssessmentPermissions.objects.get(user = userObj, instituion = instObj, assessment = assessmentObj)
					permObj.access = True
					permObj.save()
				except :
					permObj = UserAssessmentPermissions(user = userObj, instituion = instObj, assessment = assessmentObj, access=True)
					permObj.save()
	assignedAsmIds = list(set(assignedAsmIds))
	return assignedAsmIds	

def KLP_Users_list(request):
	""" This method is used to list out active(1) users other than staff and super users"""
	# get logged in user
	user = request.user
	if user.id:
		# check logged in user permissions, to get user list
		check_user_perm.send(sender=None, user=user, model='Users', operation=None)
		check_user_perm.connect(KLP_user_Perm)
		# get all active(1) users list other than staff and super user order by username
		user_list = User.objects.filter(is_active=1, is_staff=0, is_superuser=0).order_by("username")
		# render show users form with users list
		return render_to_response('viewtemplates/show_users_form.html',{'user_list':user_list, 'user':user, 'title':'KLP Users', 'legend':'Karnataka Learning Partnership', 'entry':"Add"})     
	else:
		# if user is not logged in redirect to login page
		return HttpResponseRedirect('/login/')
		
def KLP_User_Delete(request, user_id):
	""" This method is used to delete(deactivate) user"""
	# get logged in user
	user = request.user
	if user.id:
		# check logged in user permissions to delete user
		check_user_perm.send(sender=None, user=user, model='Users', operation=None)
		check_user_perm.connect(KLP_user_Perm)
		import random
		import string
		rangeNum = 8
		# generate random string to replace existing password.
		randomStr = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(rangeNum))
		# get user object
		userObj = User.objects.get(pk=user_id)		
		userObj.is_active = 0  # deactivate user
		userObj.set_password(randomStr) # replace password with random string
		userObj.save()  # save user object
		return render_to_response('viewtemplates/userAction_done.html',{'user':request.user,'selUser':userObj,'message':'User Deletion Successful', 'legend':'Karnataka Learning Partnership', 'entry':"Add"})       
	else:
		# if user is not logged in redirect to login page
		return HttpResponseRedirect('/login/')
	
def KLP_User_Permissions(request, user_id):
	""" This method is used to show tree for the selected user to show permissions"""
	# get logged in user
	user = request.user
	if user.id:
		# check logged in user permissions 
		check_user_perm.send(sender=None, user=user, model='Users', operation=None)
		check_user_perm.connect(KLP_user_Perm)
		# get user object 
		userObj = User.objects.get(pk=user_id)
		# get all boundary types
		boundType_List = Boundary_Type.objects.all()
		try:
			sessionVal = int(request.session['session_sch_typ'])
		except:
			sessionVal = 0
		# render user permissions template	
		return render_to_response('viewtemplates/user_permissions.html',{'userId':user_id, 'userName':userObj.username, 'boundType_List':boundType_List, 'home':True, 'session_sch_typ':sessionVal, 'entry':"Add",  'shPerm':True, 'title':'KLP Permissions', 'legend':'Karnataka Learning Partnership'}, context_instance=RequestContext(request))
	else:
		# if user is not logged in redirect to login page
		return HttpResponseRedirect('/login/')
	
	
def KLP_Show_Permissions(request, boundary_id, user_id):
	""" This method is used to show user permissions """
	userObj = User.objects.get(pk=user_id) # get user object 
	boundType_List = Boundary_Type.objects.all()  # get all boundary types
	# get session value, if session is not set default value is 0
	try:
		sessionVal = int(request.session['session_sch_typ'])
	except:
		sessionVal = 0
	redUrl = '/list/%s/user/%s/permissions/' %(boundary_id, user_id)
	# get all assigned institutions to the user
	assignedInst = Institution.objects.select_related("boundary").filter(Q(boundary__id=boundary_id)|Q(boundary__parent__id=boundary_id)|Q(boundary__parent__parent__id=boundary_id), active=2).extra(where=['''schools_institution.id in (SELECT "obj_id" FROM "public"."object_permissions_institution_perms" WHERE "user_id" = '%s' AND "Acess" = 't')''' %(user_id)]).only("id", "name", "boundary").order_by("boundary", "boundary__parent", "name")
	
	assignedInstIds = assignedInst.values_list("id", flat=True)
	# get unassigned institutions based on assigned institutions
	unAssignedInst = Institution.objects.select_related("boundary").filter(Q(boundary__id=boundary_id)|Q(boundary__parent__id=boundary_id)|Q(boundary__parent__parent__id=boundary_id), active=2).exclude(pk__in=assignedInstIds).only("id", "name", "boundary").order_by("boundary", "boundary__parent", "name")
	
	
	# get all assigned assessment objects
	assignedpermObjects = UserAssessmentPermissions.objects.select_related("assessment", "instituion").filter(Q(instituion__boundary__id=boundary_id)|Q(instituion__boundary__parent__id=boundary_id)|Q(instituion__boundary__parent__parent__id=boundary_id), user=userObj, access=True).defer("access").order_by("instituion__boundary", "instituion__boundary__parent", "instituion__name",)
	
	
	
	unMapObjs = Assessment_StudentGroup_Association.objects.select_related("student_group", "assessment").filter(Q(student_group__institution__boundary__id=boundary_id)|Q(student_group__institution__boundary__parent__id=boundary_id)|Q(student_group__institution__boundary__parent__parent__id=boundary_id), active=2).defer("active").order_by("student_group__institution__boundary", "student_group__institution__boundary__parent", "student_group__institution__name")
	for assignedPermObj in assignedpermObjects:
		qsets = (
	            Q(assessment = assignedPermObj.assessment)&
	            Q(student_group__institution = assignedPermObj.instituion)
	        )
		unMapObjs = unMapObjs.exclude(qsets)
	unMapList = unMapObjs.values_list("student_group__institution", "assessment").distinct()
	# get all unassigned assessment objects
	qList=[Assessment_StudentGroup_Association.objects.select_related("student_group", "assessment").filter(student_group__institution__id=unMapVal[0], assessment__id=unMapVal[1]).defer("active")[0] for unMapVal in unMapList]
	
	return render_to_response('viewtemplates/show_permissions.html',{'assignedInst':assignedInst,  'userId':user_id, 'userName':userObj.username, 'unAssignedInst':unAssignedInst, 'assignedpermObjects':assignedpermObjects, 'redUrl':redUrl, 'qList':qList}, context_instance=RequestContext(request))		
	
def KLP_Show_User_Permissions(request, boundary_id, user_id):	
	return render_to_response('viewtemplates/show_permissions.html',{'userId':user_id, 'boundary_id':boundary_id, 'confirmMsg':True}, context_instance=RequestContext(request))	 
	
	
def KLP_Revoke_Permissions(request, permissionType):
	""" This method is used to revoke user permissions"""
	# check logged in user permissions
	check_user_perm.send(sender=None, user=request.user, model='Users', operation=None)
	check_user_perm.connect(KLP_user_Perm)
	# get user id to revoke permissions
	user_id = request.POST.get('userId')
	opStatus = "success"
	try:	
		if permissionType == 'permissions':
			# if permissiontype is permissions revoke institution permissions for the user
			userObj = User.objects.get(pk=user_id)
			# get institution list to revoke
			instList = request.POST.getlist('assignedInst')
			for inst_id in instList:
				instObj = Institution.objects.get(pk=inst_id)
				# revoke permission for user
				userObj.revoke('Acess', instObj)
		else:
			# else revoke assessment permissions
			assignedAsmList = request.POST.getlist('assignedAsm')
			for userAsm_id in assignedAsmList:
				# get UserAssessmentPermissions object
				permObj = UserAssessmentPermissions.objects.get(pk=userAsm_id)
				permObj.access = False  # revoke permissions
				permObj.save()
	except:
		opStatus = "fail"		
	# if revoke permission fail return response as fail else return success.
	return HttpResponse(opStatus)
	
def KLP_ReAssign_Permissions(request, permissionType):
	""" This method is used to reassign permissions to user"""
	# check logged in user permissions
	check_user_perm.send(sender=None, user=request.user, model='Users', operation=None)
	check_user_perm.connect(KLP_user_Perm)
	#get selected users list
	userList = request.POST.getlist('userId')
	permissions = ['Acess']
	opStatus = "success"
	try:
		if permissionType== 'permissions':
			# if permissionsType is permissions assign instituions to user
			inst_list = request.POST.getlist('unassignedInst') # get selected institution list
			assignPermission(inst_list, userList, permissions, permissionType, None, True) # call assignPermission method to assign permission
		else:
			# else assign assessments to user
			asmList = request.POST.getlist('unassignedAsm') # get selected assesment and institution list
			for asm in asmList:
				asm_list = asm.split("_")
				inst_list = [asm_list[0]]
				assessmentId = asm_list[1]
				assignPermission(inst_list, userList, permissions, permissionType, assessmentId) # call assignPermission method to assign permission
	except:
		opStatus = "fail"	
	# if reassign permission fail return response as fail else return success.	
	return HttpResponse(opStatus)

urlpatterns = patterns('',             
   url(r'^assign/permissions/?$', KLP_Assign_Permissions),
   url(r'^list/users/?$', KLP_Users_list),
   url(r'^user/(?P<user_id>\d+)/delete?$', KLP_User_Delete),
   url(r'^user/(?P<user_id>\d+)/permissions/?$', KLP_User_Permissions),
   url(r'^list/(?P<boundary_id>\d+)/user/(?P<user_id>\d+)/permissions/?$', KLP_Show_Permissions),
   url(r'^revoke/user/(?P<permissionType>\w+)/?$', KLP_Revoke_Permissions),
   url(r'^assign/user/(?P<permissionType>\w+)/?$', KLP_ReAssign_Permissions),
   url(r'^show/(?P<boundary_id>\d+)/user/(?P<user_id>\d+)/permissions/?$', KLP_Show_User_Permissions),
)
