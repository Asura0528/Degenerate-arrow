var vm = new Vue({
    el: '#app',
    // 修改Vue变量的读取语法，避免和django模板语法冲突
    delimiters: ['[[', ']]'],
    data: {
        host,
        show_menu:false,
        username:'',
        is_login:false
    },
    mounted(){
        this.username=getCookie('username');
        this.is_login=getCookie('is_login');
    },
    methods: {
        //显示下拉菜单
        show_menu_click:function(){
            this.show_menu = !this.show_menu ;
        }
    }
});

$(function () {
    // body...
    $(".informationBox").bind("webkitAnimationEnd",function () {
        // body...
        if (!$(".informationBox").is(":animated")) {
            $(".informationBox").css({
                "background-size": "200% 100%",
                "animation": "ibcbgposition 20s infinite linear alternate",
            })
        }
    });
    if ($.cookie('is_login')){
        $(".imgBox").css(
            "margin-bottom", "10px"
        )
    }
});
window.onload = function() {
    if(document.body.scrollTop > 0) {
        console.log(1);
        window.scrollTo(0, -1);
        document.body.scrollTop = 0;
    }
    window.scrollTo(0, -1);
    document.body.scrollTop = 0;
};
