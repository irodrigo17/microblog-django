from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from microblog_app.models import *
import logging
from django.shortcuts import redirect
from django.contrib import messages
from django.template import RequestContext

# Get an instance of a logger
logger = logging.getLogger(__name__)

@csrf_exempt # TODO: configure csrf properly
def reset_password(request):
    uuid = request.GET['uuid']
    lost_password = get_object_or_404(LostPassword, uuid=uuid)
    logger.debug('lost_password: %s' % str(lost_password))
    user = get_object_or_404(User, email=lost_password.email)
    logger.debug('user: %s' % str(user))
    return render_to_response('reset_password.html', {'lost_password': lost_password, 'user': user})

@csrf_exempt # TODO: configure csrf properly
def update_password(request):
    new_password = request.POST['new_password']
    logger.debug('new_password: %s' % new_password)
    confirmation = request.POST['confirmation']
    logger.debug('confirmation: %s' % confirmation)
    if new_password != confirmation:
        messages.error(request, "Passwords don't match")
        return redirect('/resetpasswordresult/')

    uuid = request.POST['uuid']
    logger.debug('uuid: %s' % uuid)
    lost_password = get_object_or_404(LostPassword, uuid=uuid)
    logger.debug('lost_password: %s' % str(lost_password))
    user = get_object_or_404(User, email=lost_password.email)
    logger.debug('user: %s' % str(user))

    lost_password.new_password = new_password
    lost_password.save()
    messages.success(request, 'Password updated successfuly!')
    return redirect('/resetpasswordresult/')

def reset_password_result(request):
    return render_to_response('reset_password_result.html', {}, context_instance=RequestContext(request))

