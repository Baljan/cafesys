from django_assets import Bundle, register

js = Bundle(
        'js/jquery-1.4.2.min.js',
        #'pinax/js/base.js',
        'js/jquery.plugins.js',
        'js/jquery-ui-*.min.js',
        'js/uni-form.jquery.js',
        'js/baljan.js',
        filters='uglifyjs', 
        output='gen/baljan.js')
register('js_all', js)

css = Bundle(
        'uni_form/uni-form.css',
        'uni_form/default.uni-form.css',
        'css/960.css',
        'css/flick/jquery-ui-1.8.2.custom.css',
        'css/site_base.css',
        'css/baljan.css',
        filters='cssmin', 
        output='gen/baljan.css')
register('css_all', css)
