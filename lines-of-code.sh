set -e

total_lines=0
python_dirs="
cardreader 
cafesys/baljan
"
python_lines=0
for d in $python_dirs; do
    python_lines=$(($python_lines + $(find $d -type f -name '*.py' | xargs cat | wc -l )))
done
total_lines=$(($total_lines + $python_lines))

template_dirs='
cafesys/templates/baljan
'
templates_lines=0
for d in $template_dirs; do
    templates_lines=$(($templates_lines + $(find $d -type f -name '*.html' | xargs cat | wc -l )))
done
total_lines=$(($total_lines + $templates_lines))

css_files='
cafesys/media/css/baljan.css
'
css_lines=0
for f in $css_files; do
    css_lines=$(($css_lines + $(cat $f | wc -l)))
done
total_lines=$(($total_lines + $css_lines))

js_files='
cafesys/media/js/baljan.js
'
js_lines=0
for f in $js_files; do
    js_lines=$(($js_lines + $(cat $f | wc -l)))
    total_lines=$(($total_lines + $js_lines))
done

echo "total lines of code (no third party)"
printf "%10s\n"  "$total_lines"

scale=2
echo python
python_pc=$(echo "scale=2;100 * $python_lines / $total_lines" | bc)
printf "%10s %10.2f%%\n"  "$python_lines" $python_pc

echo templates
templates_pc=$(echo "scale=2;100 * $templates_lines / $total_lines" | bc)
printf "%10s %10.2f%%\n"  "$templates_lines" $templates_pc

echo css
css_pc=$(echo "scale=2;100 * $css_lines / $total_lines" | bc)
printf "%10s %10.2f%%\n"  "$css_lines" $css_pc

echo js
js_pc=$(echo "scale=2;100 * $js_lines / $total_lines" | bc)
printf "%10s %10.2f%%\n"  "$js_lines" $js_pc
