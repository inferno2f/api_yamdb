from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import (filters, generics, permissions, status,
                            viewsets, exceptions)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import SlidingToken

from reviews.models import Category, Genre, Review, Title, User
from .filters import TitleFilter
from .mixins import ListCreateDestroyViewSet
from .permissions import (AdminLevelOrReadOnlyPermission, AdminLevelPermission,
                          IsOwnerAdminModeratorOrReadOnly)
from .serializers import (CategorySerializer, CommentSerializer,
                          CreateUserSerializer, GenreSerializer,
                          GetJWTTokenSerializer, ReviewSerializer,
                          TitleCreateSerializer, TitleSerializer,
                          UserNotInfoSerializer, UserSerializer,
                          UserWithAdminAccessSerializer)


class RegisterNewUserAPIView(generics.CreateAPIView):
    serializer_class = CreateUserSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = user.confirmation_code
        send_mail(
            'Confirmation code', f'Your code: {token}', settings.ADMIN_EMAIL,
            [user.email],
            fail_silently=False,)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomJWTTokenView(generics.CreateAPIView):
    serializer_class = GetJWTTokenSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        v_data = serializer.validated_data
        user = get_object_or_404(
            User, username=v_data['username'])
        if user.confirmation_code != v_data['confirmation_code']:
            raise exceptions.ValidationError()
        token = SlidingToken.for_user(user)
        return Response({'Token': str(token)}, status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserNotInfoSerializer
    permission_classes = (AdminLevelPermission,)
    lookup_field = 'username'

    @action(methods=['get', 'patch'],
            detail=False, permission_classes=(permissions.IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        user = get_object_or_404(User, username=request.user.username)
        if request.method == 'GET':
            serializer = UserSerializer(user, many=False)
            return Response(serializer.data)
        if request.method == 'PATCH':
            if user.is_superuser:
                serializer = UserWithAdminAccessSerializer(
                    user, data=request.data, partial=True)
            else:
                serializer = UserSerializer(
                    user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.annotate(
        rating=Avg('reviews__score')
    ).order_by('-id')
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (AdminLevelOrReadOnlyPermission,)
    filterset_class = TitleFilter
    filterset_fields = ['category', 'genre', 'year', 'name']

    def get_serializer_class(self):
        if self.request.method in ['GET']:
            return TitleSerializer
        return TitleCreateSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    permission_classes = (AdminLevelOrReadOnlyPermission,)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_404_NOT_FOUND)


class GenreViewSet(ListCreateDestroyViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    lookup_field = 'slug'
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    permission_classes = (AdminLevelOrReadOnlyPermission,)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = (IsOwnerAdminModeratorOrReadOnly,)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        return title.reviews.all()

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, id=title_id)
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (IsOwnerAdminModeratorOrReadOnly,)
    http_method_names = ('get', 'post', 'patch', 'delete')

    def get_queryset(self):
        title_id = self.kwargs.get('title_id')
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id, title=title_id)
        return review.comments.all()

    def perform_create(self, serializer):
        title_id = self.kwargs.get('title_id')
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id, title=title_id)
        serializer.save(
            author=self.request.user,
            review=review
        )
