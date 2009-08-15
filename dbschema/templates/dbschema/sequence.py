revisions = [
{% for revision in revisions %}    '{{ revision|safe }}',
{% endfor %}]