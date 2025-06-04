window = {
	"name": "StakePanel",

	# Örnek konum: (SCREEN_WIDTH - 500)//2, (SCREEN_HEIGHT - 550)//2 yerine
	# sabit değer olarak 100, 50 alıyoruz
	"x": 100,
	"y": 50,

	"style": ("movable", "float"),
	"width": 500,
	"height": 550,

	"children":
	(
		{
			"name": "board",
			"type": "board_with_titlebar",

			"x": 0,
			"y": 0,
			"width": 500,
			"height": 550,

			"title": "Stake Seçenekleri",

			"children":
			(
				# Ayırıcı çizgi (isteğe bağlı)
				{
					"name": "seperator_line",
					"type": "line",
					"x": 20,
					"y": 320,
					"width": 460,
					"height": 0,
					"color": 0xff775533,
				},

				# "Aktif Stake İşlemleri" başlığı
				{
					"name": "active_stake_title",
					"type": "text",
					"x": 0,
					"y": 335,
					"text": "Aktif Stake İşlemleri",
					"horizontal_align": "center",
					"text_horizontal_align": "center",
				},

				# ScrollBar
				{
					"name": "active_stake_scroll",
					"type": "scrollbar",
					"x": 470,
					"y": 365,
					"size": 160,
				},

				# Aktif Stake İşlemleri Gösterilecek Board
				{
					"name": "active_stake_board",
					"type": "thinboard",
					"x": 30,
					"y": 365,
					"width": 440,
					"height": 160,

					"children":
					(
						{
							"name": "active_stake_container",
							"type": "listbox",
							"x": 5,
							"y": 5,
							"width": 430,
							"height": 150,
							"item_step": 25,
							"viewcount": 3,
						},
					),
				},
			),
		},
	),
}
