function processOrdersPerDayAndHour(data)
{
    Dajax.process(data);
    alert(data);
}

$(document).ready(function () {
    Dajaxice.stats.orders_per_day_and_hour('processOrdersPerDayAndHour', {
    });
});
