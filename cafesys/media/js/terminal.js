$(document).ready(function() {

        var guiSettings = {
            loadingAnimation: false,
        }

        var itemInfo = {}
        var lastBalance = 0;
        var orderCount = 0;

        $('body').unselectable();
        
        var resetOrder = function() {
            $('.item .value').each(function() {
                var itemId = $(this).parents('.item').attr('id');
                var countInit = itemInfo[itemId]['countInit'];
                var costPer = itemInfo[itemId]['costPer'];
                $.data(this, 'count', countInit);
                $.data(this, 'costPer', costPer);
            });
        }

        var totalCost = function() {
            var costTotal = 0;
            $('.item .value').each(function() {
                var count = $.data(this, 'count');
                var cost = count * $.data(this, 'costPer');
                costTotal += cost;
            });
            return costTotal;
        }

        var guiRefresh = function() {
            $('.item .value').each(function() {
                var count = $.data(this, 'count');
                var cost = count * $.data(this, 'costPer');
                $(this).html([
                    count, ' st ',
                    '(', cost, ' SEK)'
                    ].join(''));
            });
            $('.cost-total .value').html(totalCost() + ' SEK');
            $('.last-balance .value').html(lastBalance + ' SEK');
        }

        $.getJSON('item-info', function(items) {
            for (var i in items) {
                itemInfo['item-'+items[i].pk] = {
                    'costPer': items[i].fields.cost,
                    'countInit': items[i].fields.initial_count
                }
            }
            resetOrder();
            guiRefresh();
        });


        $('.item .mod').click(function() {
            var value = $(this).siblings('.value')[0];

            var cd = {
                'remove': {
                    'limitFun': Math.max,
                    'limit': 0,
                    'updateFun': function(x) { return x - 1; }
                },
                'add': {
                    'limitFun': Math.min,
                    'limit': 10,
                    'updateFun': function(x) { return x + 1; }
                }
            }
            for (var cls in cd) {
                if ($(this).hasClass(cls)) {
                    var e = cd[cls];
                    $.data(value, 'count', e['limitFun'](
                            e['limit'], e['updateFun']($.data(value, 'count'))
                            ));
                }
            }

            guiRefresh();
            if (guiSettings.loadingAnimation) {
                $('.cost-total .non-overlay').css('visibility', 'hidden');
                $('.cost-total .overlay').css('visibility', 'visible');
            }
        });
        
        var fxOrderPut = function(callback) {
            "The callback will be called when no info is shown on-screen."
            var orderContainer = $('.order-container');
            $(orderContainer).animate({ opacity: 0.0, }, 500);
            $(document).oneTime(500, callback);
            $(document).oneTime(500, function() {
                var balance = $('.last-balance');
                $(balance).animate({opacity: 0.0}, 0);
                $(balance).css('display', 'block');
                $(balance).animate({opacity: 1.0}, 500);
                $(document).oneTime(2000, function() {
                    $(balance).animate({opacity: 0.0}, 500)
                });
                $(document).oneTime(2000+500, function() {
                    $(balance).css('display', 'none');
                });
            });
            $(document).oneTime(500+500+2000, function() {
                $(orderContainer).css('margin-top', '-2000px');
                $(orderContainer).animate({ marginTop: '0px', opacity: 1.0, }, 1000);
            });
        }
        
        var pollOrderCountInterval = 1000;
        var pollOrderCount = function() {
            $(document).stopTime('pollOrderCount');
            $.getJSON('order-info', function(info) {
                var newCount = info.orderCount;
                lastBalance = info.lastBalance;
                if (orderCount == newCount) {
                    /*
                    fxOrderPut(function() {
                        resetOrder();
                        guiRefresh();
                    });
                    return;
                    */
                }
                $(document).oneTime(pollOrderCountInterval, 'pollOrderCount', pollOrderCount);
            });
        }
        $(document).oneTime(pollOrderCountInterval, 'pollOrderCount', pollOrderCount);

        $('#trig-order').click(function() {
            fxOrderPut(function() {
                resetOrder();
                guiRefresh();
            })
        });
});
