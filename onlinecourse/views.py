from typing import Any, Dict
from django.shortcuts import render
from django.http import Http404, HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled



# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'
    context_object_name = 'course'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id

from django.shortcuts import render, redirect
from .models import Enrollment, Submission

def submit(request, course_id):
    # Получение текущего пользователя и объекта курса
    user = request.user
    course = Course.objects.get(id=course_id)
    
    # Получение связанной записи регистрации
    enrollment = Enrollment.objects.get(user=user, course=course)
    
    if request.method == 'POST':
        # Создание нового объекта отправки, связанного с регистрацией
        submission = Submission.objects.create(enrollment=enrollment)
        
        # Получение выбранных вариантов из объекта HTTP-запроса
        selected_choices = extract_answers(request)
        
        # Добавление каждого выбранного варианта в объект отправки
        for choice_id in selected_choices:
            choice = Choice.objects.get(id=choice_id)
            submission.choices.add(choice)

        selected_choices.save()
        
        # Перенаправление на представление show_exam_result с идентификатором отправки
        return redirect(reverse('onlinecourse:show_exam_result', kwargs={'course_id': course_id, 'submission_id': submission.id}))
    
    raise Http404('Страница не найдена')


def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


from django.shortcuts import render
from .models import Course, Submission

def show_exam_result(request, course_id, submission_id):
    # Получение объекта курса и объекта отправки на основе их идентификаторов
    course = Course.objects.get(id=course_id)
    submission = Submission.objects.get(id=submission_id)
    
    # Получение выбранных идентификаторов выбора из записи отправки
    selected_ids = submission.choices.values_list('id', flat=True)
    print(selected_ids)
    
    # Подсчет общего балла, сложив оценки за все вопросы курса
    grade = 0
    total_score = 0
    for question in course.question.all():
        total_score += question.score
        truth = len(question.choice.filter(true=True))
        for choice in question.choice.all():
            if choice.id in selected_ids and choice.true:
                grade += question.score/truth
            if choice.id in selected_ids and not choice.true:
                grade -= question.score/truth
    
    # Добавление курса, выбранных идентификаторов и оценки в контекст для отображения HTML-страницы
    context = {
        'course': course,
        'selected_ids': selected_ids,
        'grade': grade,
        'total_score': float(total_score),
        'pass': total_score * 0.8
    }
    
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)





