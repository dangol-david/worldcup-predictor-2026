"""
seed_squads.py
--------------
Loads every team's coach + 26-man roster into the `squads` table so that
Man-of-the-Match and First-Goal-Scorer picks use real-player dropdowns.

Team keys MUST match the team names used in the fixtures (see seed_data.py) —
e.g. "Czechia" (not "Czech Republic"), "Turkiye", "Bosnia and Herzegovina",
"Democratic Republic of Congo".

Player names are stored without club affiliations (cleaner dropdowns). Squads
can still be edited any time in the app: ⚙️ Admin → "Manage squads & coaches".

Run:  python seed_squads.py            # upserts all squads (safe to re-run)
      python seed_squads.py --check    # only report coverage vs. fixtures
"""

from __future__ import annotations

import argparse

import database as db

# team -> (coach, [players...])  — keys match fixture team names exactly.
SQUADS: dict[str, tuple[str, list[str]]] = {
    # ===================== Group A =====================
    "Mexico": ("Javier Aguirre", [
        "Raul Rangel", "Carlos Acevedo", "Guillermo Ochoa",
        "Israel Reyes", "Jesús Gallardo", "Jorge Sánchez", "César Montes",
        "Johan Vásquez", "Mateo Chávez",
        "Erik Lira", "Luis Romo", "Obed Vargas", "Brian Gutiérrez",
        "Orbelín Pineda", "Edson Álvarez", "Gilberto Mora", "César Huerta",
        "Álvaro Fidalgo", "Luis Chávez",
        "Roberto Alvarado", "Alexis Vega", "Julián Quiñones",
        "Santiago Gimenez", "Guillermo Martínez", "Armando González",
        "Raúl Jiménez",
    ]),
    "South Africa": ("Hugo Broos", [
        "Sipho Chaine", "Ricardo Goss", "Ronwen Williams",
        "Aubrey Modiba", "Khuliso Mudau", "Nkosinathi Sibisi",
        "Mbekezeli Mbokazi", "Ime Okon", "Samukele Kabini",
        "Khulumani Ndamane", "Thabang Matuludi", "Kamogelo Sebelebele",
        "Bradley Cross", "Olwethy Makhanya",
        "Teboho Mokoena", "Sphephelo Sithole", "Thalente Mbatha", "Jayden Adams",
        "Themba Zwane", "Lyle Foster", "Evidence Makgopa", "Oswin Appollis",
        "Iqraam Rayners", "Relebohile Mofokeng", "Thapelo Maseko",
        "Tshepang Moremi",
    ]),
    "South Korea": ("Myung-Bo Hong", [
        "Hyeon-Woo Jo", "Seung-Gyu Kim", "Bum-Keun Song",
        "Moon-Hwan Kim", "Min-Jae Kim", "Tae-Hyon Kim", "Jin-Seob Park",
        "Young-Woo Seol", "Jens Castrop", "Ki-Hyuk Lee", "Tae-Seok Lee",
        "Han-Beom Lee", "Yu-Min Cho",
        "Jin-Gyu Kim", "Jun-Ho Bae", "Seung-Ho Paik", "Hyun-Jun Yang",
        "Ji-Sung Eom", "Kang-In Lee", "Dong-Gyeong Lee", "Jae-Sung Lee",
        "In-Beom Hwang", "Hee-Chan Hwang",
        "Heung-Min Son", "Hyeon-Gyu Oh", "Gue-Sung Cho",
    ]),
    "Czechia": ("Miroslav Koubek", [
        "Lukas Hornicek", "Matej Kovar", "Jindrich Stanek",
        "Vladimir Coufal", "David Doudera", "Tomas Holes", "Robin Hranac",
        "Stepan Chaloupek", "David Jurasek", "Ladislav Krejci",
        "Jaroslav Zeleny", "David Zima",
        "Lukas Cerv", "Vladimir Darida", "Lukas Provod", "Michal Sadilek",
        "Hugo Sochurek", "Alexandr Sojka", "Tomas Soucek", "Pavel Sulc",
        "Denis Visinsky",
        "Adam Hlozek", "Tomas Chory", "Mojmir Chytil", "Jan Kuchta",
        "Patrik Schick",
    ]),

    # ===================== Group B =====================
    "Canada": ("Jesse Marsch", [
        "Maxime Crepeau", "Owen Goodman", "Dayne St. Clair",
        "Moise Bombito", "Derek Cornelius", "Alphonso Davies",
        "Luc de Fougerolles", "Alistair Johnston", "Alfie Jones",
        "Richie Laryea", "Niko Sigur", "Joel Waterman",
        "Ali Ahmed", "Tajon Buchanan", "Mathieu Choiniere",
        "Stephen Eustaquio", "Marcelo Flores", "Ismael Kone", "Liam Millar",
        "Jonathan Osorio", "Nathan-Dylan Saliba", "Jacob Shaffelburg",
        "Jonathan David", "Promise David", "Cyle Larin", "Tani Oluwaseyi",
    ]),
    "Bosnia and Herzegovina": ("Sergej Barbarez", [
        "Nikola Vasilj", "Martin Zlomislic", "Osman Hadzikic",
        "Sead Kolasinac", "Amar Dedic", "Nihad Mujakic", "Nikola Katic",
        "Tarik Muharemovic", "Stjepan Radeljic", "Dennis Hadzikadunic",
        "Nidal Celik",
        "Amir Hadziahmetovic", "Ivan Sunjic", "Ivan Basic", "Dzenis Burnic",
        "Ermin Mahmic", "Benjamin Tahirovic", "Amar Memic", "Armin Gigovic",
        "Kerim Alajbegovic", "Esmir Bajraktarevic",
        "Ermedin Demirovic", "Jovo Lukic", "Samed Bazdar", "Haris Tabakovic",
        "Edin Dzeko",
    ]),
    "Qatar": ("Julen Lopetegui", [
        "Salah Zakaria", "Mahmoud Abunada", "Meshaal Barsham",
        "Hashmi Hussein", "Ayoub Alawi", "Boualem Khoukhi", "Pedro Miguel",
        "Issa Laaye", "Lucas Mendes", "Sultan Al-Brake", "Homam Al-Amin",
        "Mohammed Al-Manai", "Jassem Jaber", "Karim Boudiaf", "Ahmed Fathi",
        "Abdulaziz Hatem", "Assim Madibo",
        "Tahseen Mohammed", "Edmilson Junior", "Almoez Ali", "Akram Afif",
        "Mohammed Muntari", "Youssef Abdulrazzaq", "Ahmed Alaa",
        "Hassan Al-Haydos", "Ahmed Al-Janahi",
    ]),
    "Switzerland": ("Murat Yakin", [
        "Marvin Keller", "Gregor Kobel", "Yvon Mvogo",
        "Manuel Akanji", "Aurele Amenda", "Eray Comert", "Nico Elvedi",
        "Luca Jaquez", "Miro Muheim", "Ricardo Rodriguez", "Silvan Widmer",
        "Michel Aebischer", "Christian Fassnacht", "Remo Freuler",
        "Ardon Jashari", "Johan Manzambi", "Fabian Rieder", "Djibril Sow",
        "Ruben Vargas", "Granit Xhaka", "Denis Zakaria",
        "Zeki Amdouni", "Breel Embolo", "Cedric Itten", "Dan Ndoye",
        "Noah Okafor",
    ]),

    # ===================== Group C =====================
    "Brazil": ("Carlo Ancelotti", [
        "Alisson", "Ederson (Fenerbahce)", "Weverton",
        "Marquinhos", "Gabriel", "Bremer", "Ibanez", "Leo Pereira",
        "Danilo (Flamengo)", "Alex Sandro", "Douglas Santos",
        "Casemiro", "Bruno Guimaraes", "Fabinho", "Danilo (Botafogo)",
        "Lucas Paqueta", "Ederson (Atalanta)",
        "Vinicius Junior", "Raphinha", "Matheus Cunha", "Luiz Henrique",
        "Igor Thiago", "Endrick", "Gabriel Martinelli", "Rayan", "Neymar",
    ]),
    "Morocco": ("Mohamed Ouahbi", [
        "Yassine Bounou", "Munir Mohamedi", "Ahmed Tagnaouti",
        "Noussair Mazraoui", "Anass Salah-Eddine", "Youssef Belammari",
        "Nayef Aguerd", "Chadi Riad", "Issa Diop", "Redouane Halhal",
        "Achraf Hakimi", "Zakaria El Ouahdi",
        "Samir El Mourabet", "Ayyoub Bouaddi", "Neil El Aynaoui",
        "Sofyan Amrabat", "Azzedine Ounahi", "Bilal El Khannouss",
        "Ismael Saibari",
        "Abdessamad Ezzalzouli", "Chemsdine Talbi", "Soufiane Rahimi",
        "Ayoub El Kaabi", "Brahim Diaz", "Yassine Gessime",
        "Ayoub Amaimouni-Echghouyabe",
    ]),
    "Haiti": ("Sebastien Migne", [
        "Johnny Placide", "Alexandre Pierre", "Josue Duverger",
        "Carlens Arcus", "Wilguens Pauguain", "Duke Lacroix",
        "Martin Experience", "Jean-Kevin Duverne", "Ricardo Ade",
        "Hannes Delcroix", "Keeto Thermoncy",
        "Leverton Pierre", "Carl-Fred Sainthe", "Jean-Jacques Danley",
        "Jean-Ricner Bellegarde", "Pierre Woodenski", "Dominique Simon",
        "Louicius Deedson", "Ruben Providence", "Josue Casimir",
        "Derrick Etienne", "Wilson Isidor", "Duckens Nazon",
        "Frantzdy Pierrot", "Yassin Fortune", "Lenny Joseph",
    ]),
    "Scotland": ("Steve Clarke", [
        "Craig Gordon", "Angus Gunn", "Liam Kelly",
        "Grant Hanley", "Jack Hendry", "Aaron Hickey", "Dom Hyam",
        "Scott McKenna", "Nathan Patterson", "Anthony Ralston",
        "Andy Robertson", "John Souttar", "Kieran Tierney",
        "Ryan Christie", "Findlay Curtis", "Lewis Ferguson",
        "Ben Gannon-Doak", "Tyler Fletcher", "John McGinn", "Kenny McLean",
        "Scott McTominay",
        "Che Adams", "Lyndon Dykes", "George Hirst", "Lawrence Shankland",
        "Ross Stewart",
    ]),

    # ===================== Group D =====================
    "USA": ("Mauricio Pochettino", [
        "Chris Brady", "Matt Freese", "Matt Turner",
        "Max Arfsten", "Sergino Dest", "Alex Freeman", "Mark McKenzie",
        "Tim Ream", "Chris Richards", "Antonee Robinson", "Miles Robinson",
        "Joe Scally", "Auston Trusty",
        "Tyler Adams", "Sebastian Berhalter", "Weston McKennie", "Gio Reyna",
        "Cristian Roldan", "Malik Tillman",
        "Brenden Aaronson", "Folarin Balogun", "Ricardo Pepi",
        "Christian Pulisic", "Tim Weah", "Haji Wright", "Alejandro Zendejas",
    ]),
    "Paraguay": ("Gustavo Alfaro", [
        "Roberto Junior Fernandez", "Orlando Gill", "Gaston Olveira",
        "Omar Alderete", "Junior Alonso", "Fabian Balbuena",
        "Juan Jose Caceres", "Jose Canale", "Gustavo Gomez",
        "Alexandro Maidana", "Gustavo Velazquez",
        "Damian Bobadilla", "Gustavo Caballero", "Andres Cubas",
        "Matias Galarza", "Diego Gomez", "Mauricio Magalhaes",
        "Briaian Ojeda", "Alejandro Romero",
        "Miguel Almiron", "Gabriel Avalos", "Alex Arce", "Julio Enciso",
        "Isidro Pitta", "Antonio Sanabria", "Ramon Sosa",
    ]),
    "Australia": ("Tony Popovic", [
        "Maty Ryan", "Paul Izzo", "Patrick Beach",
        "Aziz Behich", "Jordan Bos", "Cameron Burgess", "Alessandro Circati",
        "Milos Degenek", "Jason Geria", "Lucas Herrington", "Jacob Italiano",
        "Harry Souttar", "Kai Trewin",
        "Cameron Devlin", "Ajdin Hrustic", "Jackson Irvine",
        "Connor Metcalfe", "Aiden O'Neill", "Paul Okon-Engstler",
        "Nestory Irankunda", "Mathew Leckie", "Awer Mabil", "Mohamed Toure",
        "Nishan Velupillay", "Cristian Volpato", "Tete Yengi",
    ]),
    "Turkiye": ("Vincenzo Montella", [
        "Ugurcan Cakir", "Altay Bayindir", "Mert Gunok",
        "Ferdi Kadioglu", "Merih Demiral", "Zeki Celik", "Ozan Kabak",
        "Mert Muldur", "Abdulkerim Bardakci", "Eren Elmali", "Caglar Soyuncu",
        "Samet Akaydin",
        "Arda Guler", "Can Uzun", "Orkun Kokcu", "Hakan Calhanoglu",
        "Ismail Yuksek", "Kaan Ayhan", "Salih Ozcan",
        "Kenan Yildiz", "Baris Alper Yilmaz", "Kerem Akturkoglu",
        "Yunus Akgun", "Oguz Aydin", "Deniz Gul", "Irfan Can Kahveci",
    ]),

    # ===================== Group E =====================
    "Germany": ("Julian Nagelsmann", [
        "Oliver Baumann", "Manuel Neuer", "Alexander Nubel",
        "Waldemar Anton", "Nathaniel Brown", "David Raum", "Antonio Rudiger",
        "Nico Schlotterbeck", "Jonathan Tah", "Malick Thiaw",
        "Pascal Gross", "Joshua Kimmich", "Felix Nmecha",
        "Aleksandar Pavlovic", "Angelo Stiller", "Leon Goretzka",
        "Florian Wirtz", "Jamie Leweling",
        "Maximilian Beier", "Kai Havertz", "Assan Ouedraogo", "Jamal Musiala",
        "Leroy Sane", "Deniz Undav", "Nick Woltemade",
    ]),
    "Curacao": ("Dick Advocaat", [
        "Tyrick Bodak", "Trevor Doornbusch", "Eloy Room",
        "Riechedly Bazoer", "Joshua Brenet", "Roshon van Eijma",
        "Sherel Floranus", "Deveron Fonville", "Jurien Gaari",
        "Armando Obispo", "Shurandy Sambo",
        "Juninho Bacuna", "Leandro Bacuna", "Livano Comenencia",
        "Kevin Felida", "Ar'Jany Martha", "Tyrese Noslin",
        "Godfried Roemeratoe",
        "Jeremy Antonisse", "Tahith Chong", "Kenji Gorre", "Sontje Hansen",
        "Gervane Kastaneer", "Brandley Kuwas", "Jurgen Locadia",
        "Jearl Margaritha",
    ]),
    "Ivory Coast": ("Emerse Fae", [
        "Yahia Fofana", "Mohamed Kone", "Alban Lafont",
        "Emmanuel Agbadou", "Clement Akpa", "Ousmane Diomande", "Guela Doue",
        "Ghislain Konan", "Odilon Kossounou", "Evan Ndicka", "Wilfried Singo",
        "Seko Fofana", "Parfait Guiagon", "Christ Inao Oulai", "Franck Kessie",
        "Ibrahim Sangare", "Jean-Michael Seri",
        "Simon Adingra", "Ange-Yoan Bonny", "Amad Diallo", "Oumar Diakite",
        "Yan Diomande", "Evann Guessand", "Nicolas Pepe", "Bazoumana Toure",
        "Elye Wahi",
    ]),
    "Ecuador": ("Sebastian Beccacece", [
        "Hernan Galindez", "Moises Ramirez", "Gonzalo Valle",
        "Piero Hincapie", "Willian Pacho", "Pervis Estupinan", "Felix Torres",
        "Joel Ordonez", "Jackson Porozo", "Angelo Preciado",
        "Moises Caicedo", "Alan Franco", "Kendry Paez", "Pedro Vite",
        "Jordy Alcivar", "Denil Castillo", "Yaimar Medina",
        "Enner Valencia", "Kevin Rodriguez", "Jordy Caicedo", "Nilson Angulo",
        "Anthony Valencia", "Jeremy Arevalo",
    ]),

    # ===================== Group F =====================
    "Netherlands": ("Ronald Koeman", [
        "Bart Verbruggen", "Mark Flekken", "Robin Roefs",
        "Virgil van Dijk", "Jan Paul van Hecke", "Nathan Ake",
        "Micky van de Ven", "Denzel Dumfries", "Jorrel Hato", "Jurrien Timber",
        "Frenkie de Jong", "Tijjani Reijnders", "Justin Kluivert",
        "Quinten Timber", "Teun Koopmeiners", "Ryan Gravenberch",
        "Marten de Roon", "Guus Til", "Mats Weiffer",
        "Cody Gakpo", "Donyell Malen", "Brian Brobbey", "Noa Lang",
        "Memphis Depay", "Wout Weghorst", "Crysencio Summerville",
    ]),
    "Japan": ("Hajime Moriyasu", [
        "Tomoki Hayakawa", "Keisuke Osako", "Zion Suzuki",
        "Yuto Nagatomo", "Shogo Taniguchi", "Ko Itakura",
        "Tsuyoshi Watanabe", "Takehiro Tomiyasu", "Hiroki Ito", "Ayumu Seko",
        "Yukinari Sugawara", "Junosuke Suzuki",
        "Wataru Endo", "Junya Ito", "Daichi Kamada", "Koki Ogawa",
        "Daizen Maeda", "Ritsu Doan", "Ao Tanaka", "Kaishu Sano",
        "Takefusa Kubo",
        "Ayase Ueda", "Keito Nakamura", "Ito Suzuki", "Kento Shiode",
        "Keisuke Goto",
    ]),
    "Sweden": ("Graham Potter", [
        "Viktor Johansson", "Kristoffer Nordfeldt", "Jacob Widell Zetterstrom",
        "Hjalmar Ekdal", "Gabriel Gudmundsson", "Isak Hien", "Emil Holm",
        "Gustaf Lagerbielke", "Victor Lindelof", "Erik Smith", "Carl Starfelt",
        "Elliot Stroud", "Daniel Svensson",
        "Taha Ali", "Yasin Ayari", "Lucas Bergvall", "Jesper Karlstrom",
        "Ken Sema", "Mattias Svanberg", "Besfort Zeneli",
        "Alexander Bernhardsson", "Anthony Elanga", "Viktor Gyokeres",
        "Alexander Isak", "Gustaf Nilsson", "Benjamin Nygren",
    ]),
    "Tunisia": ("Sabri Lamouchi", [
        "Sabri Ben Hessen", "Abdelmouhib Chamakh", "Aymen Dahman",
        "Ali Abdi", "Adem Arous", "Mohamed Amine Ben Hamida", "Dylan Bronn",
        "Raed Chikhaoui", "Moutaz Neffati", "Omar Rekik", "Montassar Talbi",
        "Yan Valery",
        "Mortadha Ben Ouanes", "Anis Ben Slimane", "Ismael Gharbi",
        "Rani Khedira", "Mohamed Hadj Mahmoud", "Hannibal Mejbri",
        "Ellyes Skhiri",
        "Elias Achouri", "Khalil Ayari", "Firas Chaouat", "Rayan Elloumi",
        "Hazem Mastouri", "Elias Saad", "Sebastian Tounekti",
    ]),

    # ===================== Group G =====================
    "Belgium": ("Rudi Garcia", [
        "Thibaut Courtois", "Senne Lammens", "Mike Penders",
        "Timothy Castagne", "Zeno Debast", "Maxim De Cuyper", "Koni De Winter",
        "Brandon Mechele", "Thomas Meunier", "Nathan Ngoy", "Joaquin Seys",
        "Arthur Theate",
        "Kevin De Bruyne", "Amadou Onana", "Nicolas Raskin", "Youri Tielemans",
        "Hans Vanaken", "Axel Witsel",
        "Charles De Ketelaere", "Jeremy Doku", "Matias Fernandez-Pardo",
        "Romelu Lukaku", "Dodi Lukebakio", "Diego Moreira",
        "Alexis Saelemaekers", "Leandro Trossard",
    ]),
    "Egypt": ("Hossam Hassan", [
        "Mohamed El Shenawy", "Mostafa Shobeir", "El Mahdi Soliman",
        "Mohamed Alaa",
        "Mohamed Hany", "Tarek Alaa", "Hamdy Fathy", "Rami Rabia",
        "Yasser Ibrahim", "Hossam Abdelmaguid", "Mohamed Abdelmonemn",
        "Ahmed Fatouh", "Karim Hafez",
        "Marwan Ateya", "Mohanad Lasheen", "Nabil Emad", "Mahmoud Saber",
        "Ahmed Zizo", "Emam Ashour", "Mostafa Ziko", "Mahmoud Trezeguet",
        "Ibrahim Adel", "Haissem Hassan",
        "Omar Marmoush", "Mohamed Salah", "Aqtay Abdallah", "Hamza Abdelkarim",
    ]),
    "Iran": ("Amir Ghalenoei", [
        "Alireza Beiranvand", "Seyed Hossein Hosseini", "Payam Niazmand",
        "Danial Eiri", "Ehsan Hajsafi", "Saleh Hardani", "Hossein Kanaani",
        "Shoja Khalilzadeh", "Milad Mohammadi", "Ali Nemati", "Ramin Rezaeian",
        "Rouzbeh Cheshmi", "Saeid Ezatolahi", "Mehdi Ghaedi", "Saman Ghoddos",
        "Mohammad Ghorbani", "Alireza Jahanbakhsh", "Mohammad Mohebi",
        "Amir Mohammad Razzaghinia", "Mehdi Torabi", "Aria Yousefi",
        "Ali Alipour", "Dennis Dargahi", "Amirhossein Hosseinzadeh",
        "Mehdi Taremi", "Shahriar Moghanlou",
    ]),
    "New Zealand": ("Darren Bazeley", [
        "Max Crocombe", "Alex Paulsen", "Michael Woud",
        "Tim Payne", "Francis De Vries", "Tyler Bindon", "Michael Boxall",
        "Liberato Cacace", "Nando Pijnaker", "Finn Surman", "Callan Elliot",
        "Tommy Smith",
        "Joe Bell", "Matt Garbett", "Marko Stamenic", "Sarpreet Singh",
        "Alex Rufer", "Ryan Thomas",
        "Chris Wood", "Eli Just", "Kosta Barbarouses", "Ben Waine", "Ben Old",
        "Callum McCowatt", "Jesse Randall", "Lachlan Bayliss",
    ]),

    # ===================== Group H =====================
    "Spain": ("Luis de la Fuente", [
        "Unai Simon", "David Raya", "Joan Garcia",
        "Aymeric Laporte", "Marc Cucurella", "Marcos Llorente", "Eric Garcia",
        "Pedro Porro", "Alex Grimaldo", "Pau Cubarsi", "Marc Pubill",
        "Rodri", "Fabian Ruiz", "Mikel Merino", "Pedri", "Gavi",
        "Martin Zubimendi", "Alex Baena",
        "Ferran Torres", "Mikel Oyarzabal", "Dani Olmo", "Nico Williams",
        "Lamine Yamal", "Yeremy Pino", "Borja Iglesias", "Victor Munoz",
    ]),
    "Cape Verde": ("Bubista", [
        "Vozinha", "Marcio Rosa", "CJ dos Santos",
        "Stopira", "Roberto Lopes", "Joao Paulo", "Diney", "Logan Costa",
        "Steven Moreira", "Wagner Pina", "Sidny Lopes Cabral", "Kelvin Pires",
        "Jamiro Monteiro", "Kevin Pina", "Deroy Duarte", "Telmo Arcanjo",
        "Laros Duarte", "Yannick Semedo",
        "Ryan Mendes", "Garry Rodrigues", "Willy Semedo", "Jovane Cabral",
        "Gilson Tavares", "Dailon Livramento", "Helio Varela", "Nuno da Costa",
    ]),
    "Saudi Arabia": ("Georgios Donis", [
        "Mohammed Al Owais", "Nawaf Al Aqidi", "Ahmed Al Kassar",
        "Abdulelah Al Amri", "Hassan Tambakti", "Jehad Thikri", "Ali Lajami",
        "Hassan Kadesh", "Saud Abdulhamid", "Mohammed Abu Al Shamat",
        "Ali Majrashi", "Moteb Al Harbi", "Nawaf Boushal", "Sultan Al-Ghannam",
        "Mohammed Kanno", "Abdullah Al Khaibari", "Ziyad Al Johani",
        "Nasser Al Dawsari", "Musab Al Juwayr", "Alaa Al Hajji",
        "Salem Al Dawsari", "Khalid Al Ghannam", "Ayman Yahya",
        "Firas Al Buraikan", "Saleh Al Shehri", "Abdullah Al Hamdan",
    ]),
    "Uruguay": ("Marcelo Bielsa", [
        "Sergio Rochet", "Fernando Muslera", "Santiago Mele",
        "Guillermo Varela", "Ronald Araujo", "Jose Maria Gimenez",
        "Santiago Bueno", "Sebastian Caceres", "Mathias Olivera",
        "Joaquin Piquerez", "Matias Vina", "Juan Manuel Sanabria",
        "Manuel Ugarte", "Emiliano Martinez (Palmeiras)", "Rodrigo Bentancur",
        "Federico Valverde", "Agustin Canobbio", "Giorgian de Arrascaeta",
        "Nicolas de la Cruz", "Facundo Pellistri", "Rodrigo Zalazar",
        "Maxi Araujo", "Brian Rodriguez",
        "Rodrigo Aguirre", "Federico Vinas", "Darwin Nunez",
    ]),

    # ===================== Group I =====================
    "France": ("Didier Deschamps", [
        "Mike Maignan", "Robin Risser", "Brice Samba",
        "Lucas Digne", "Malo Gusto", "Lucas Hernandez", "Theo Hernandez",
        "Ibrahima Konate", "Jules Kounde", "Maxence Lacroix", "William Saliba",
        "Dayot Upamecano",
        "N'Golo Kante", "Manu Kone", "Adrien Rabiot", "Aurelien Tchouameni",
        "Warren Zaire-Emery",
        "Maghnes Akliouche", "Bradley Barcola", "Rayan Cherki",
        "Ousmane Dembele", "Desire Doue", "Jean-Philippe Mateta",
        "Kylian Mbappe", "Michael Olise", "Marcus Thuram",
    ]),
    "Senegal": ("Pape Thiaw", [
        "Edouard Mendy", "Mory Diaw", "Yehvann Diouf",
        "Krepin Diatta", "Antoine Mendy", "Kalidou Koulibaly",
        "El Hadji Malick Diouf", "Mamadou Sarr", "Moussa Niakhate",
        "Moustapha Mbow", "Abdoulaye Seck", "Ismail Jakobs", "Ilay Camara",
        "Idrissa Gana Gueye", "Pape Gueye", "Lamine Camara", "Habib Diarra",
        "Pathe Ciss", "Pape Matar Sarr", "Bara Sapoko Ndiaye",
        "Sadio Mane", "Ismaila Sarr", "Iliman Ndiaye", "Assane Diao",
        "Ibrahim Mbaye", "Nicolas Jackson", "Bamba Dieng", "Cherif Ndiaye",
    ]),
    "Iraq": ("Graham Arnold", [
        "Fahad Talib", "Jalal Hassan", "Ahmed Basil",
        "Hussein Ali", "Manaf Younis", "Mustafa Saadoon",
        "Ahmed Hassan Makenzie", "Zaid Tahseen", "Rebin Sulaka",
        "Akam Hashim", "Merchas Doski", "Zaid Ismail", "Frans Putros",
        "Amir Al-Ammari", "Kevin Yakob", "Zidane Iqbal", "Aimar Sher",
        "Ibrahim Bayesh", "Ahmed Qasem", "Youssef Amyn", "Marko Farji",
        "Ali Jassim", "Ali Al-Hamadi", "Ali Yousef", "Aymen Hussein",
        "Mohanad Ali",
    ]),
    "Norway": ("Stale Solbakken", [
        "Orjan Haskjold Nyland", "Egil Selvik", "Sander Tangvik",
        "Julian Ryerson", "Marcus Holmgren Pedersen", "David Moller Wolfe",
        "Fredrik Bjorkan", "Kristoffer Ajer", "Torbjorn Heggem",
        "Leo Skiri Ostigard", "Sondre Langas", "Henrik Falchener",
        "Martin Odegaard", "Sander Berge", "Fredrik Aursnes", "Patrick Berg",
        "Kristian Thorstvedt", "Morten Thorsby", "Thelo Aasgaard",
        "Erling Haaland", "Alexander Sorloth", "Jorgen Strand Larsen",
        "Antonio Nusa", "Oscar Bobb", "Andreas Schjelderup",
        "Jens Petter Hauge",
    ]),

    # ===================== Group J =====================
    "Argentina": ("Lionel Scaloni", [
        "Emiliano Martinez", "Juan Musso", "Geronimo Rulli",
        "Leonardo Balerdi", "Lisandro Martinez", "Facundo Medina",
        "Nahuel Molina", "Gonzalo Montiel", "Nicolas Otamendi",
        "Cristian Romero", "Nicolas Tagliafico",
        "Valentin Barco", "Rodrigo De Paul", "Enzo Fernandez",
        "Giovani Lo Celso", "Alexis Mac Allister", "Exequiel Palacios",
        "Leandro Paredes",
        "Thiago Almada", "Julian Alvarez", "Nicolas Gonzalez",
        "Jose Manuel Lopez", "Lautaro Martinez", "Lionel Messi", "Nicolas Paz",
        "Giuliano Simeone",
    ]),
    "Algeria": ("Vladimir Petkovic", [
        "Luca Zidane", "Oussama Benbot", "Melvin Mastil",
        "Aissa Mandi", "Ramy Bensebaini", "Mohamed Amine Tougai",
        "Rayan Ait-Nouri", "Jaouen Hadjam", "Rafik Belghali",
        "Zineddine Belaid", "Achref Abada", "Samir Chergui",
        "Nabil Bentaleb", "Ramiz Zerrouki", "Hicham Boudaoui", "Fares Chaibi",
        "Houssem Aouar", "Ibrahim Maza", "Yacine Titraoui",
        "Riyad Mahrez", "Mohamed Amoura", "Amine Gouiri", "Anis Hadj Moussa",
        "Adil Boulbina", "Nadhir Benbouali", "Fares Ghedjemis",
    ]),
    "Austria": ("Ralf Rangnick", [
        "Alexander Schlager", "Florian Wiegele", "Patrick Pentz",
        "David Affengruber", "Kevin Danso", "Stefan Posch", "David Alaba",
        "Philipp Lienhart", "Phillipp Mwene", "Alexander Prass",
        "Marco Friedl", "Michael Svoboda",
        "Xaver Schlager", "Nicolas Seiwald", "Marcel Sabitzer",
        "Florian Grillitsch", "Carney Chukwuemeka", "Romano Schmid",
        "Konrad Laimer", "Patrick Wimmer", "Paul Wanner", "Alessandro Schopf",
        "Marko Arnautovic", "Michael Gregoritsch", "Sasa Kalajdzic",
    ]),
    "Jordan": ("Jamal Sellami", [
        "Yazeed Abulaila", "Abdallah Al-Fakhouri", "Nour Bani Attiah",
        "Ihsan Haddad", "Yazan Al-Arab", "Abdallah Nasib",
        "Mohammad Abu Hashish", "Saed Al-Rosan", "Husam Abu Dahab",
        "Mo Abualnadi", "Salim Obaid", "Anas Badawi",
        "Rajaei Ayed", "Noor Al-Rawabdeh", "Ibrahim Sadeh", "Nizar Al-Rashdan",
        "Mohannad Abu Taha", "Amer Jamous", "Mohammad Al-Dawoud",
        "Musa Al-Taamari", "Mahmoud Al-Mardi", "Ali Olwan",
        "Mohammad Abu Zrayq", "Odeh Al-Fakhouri", "Ibrahim Sabra",
        "Ali Azaizeh",
    ]),

    # ===================== Group K =====================
    "Portugal": ("Roberto Martinez", [
        "Diogo Costa", "Jose Sa", "Rui Silva", "Ricardo Velho",
        "Diogo Dalot", "Matheus Nunes", "Nelson Semedo", "Joao Cancelo",
        "Nuno Mendes", "Goncalo Inacio", "Renato Veiga", "Ruben Dias",
        "Tomas Araujo",
        "Ruben Neves", "Samuel Costa", "Joao Neves", "Vitinha",
        "Bruno Fernandes", "Bernardo Silva",
        "Joao Felix", "Francisco Trincao", "Francisco Conceicao", "Pedro Neto",
        "Rafael Leao", "Goncalo Guedes", "Goncalo Ramos", "Cristiano Ronaldo",
    ]),
    "Democratic Republic of Congo": ("Sebastien Desabre", [
        "Matthieu Epolo", "Timothy Fayulu", "Lionel Mpasi",
        "Dylan Batubinsika", "Rocky Bushiri", "Gedeon Kalulu", "Steve Kapuadi",
        "Joris Kayembe", "Arthur Masuaku", "Chancel Mbemba", "Axel Tuanzebe",
        "Aaron Wan-Bissaka",
        "Theo Bongonda", "Brian Cipenga", "Meshack Elia", "Gael Kakuta",
        "Edo Kayembe", "Nathanael Mbuku", "Samuel Moutoussamy",
        "Ngal'ayel Mukau", "Charles Pickel", "Noah Sadiki",
        "Cedric Bakambu", "Simon Banza", "Fiston Mayele", "Yoane Wissa",
    ]),
    "Uzbekistan": ("Fabio Cannavaro", [
        "Utkir Yusupov", "Abduvohid Nematov", "Botirali Ergashev",
        "Rustam Ashurmatov", "Farrukh Sayfiev", "Khojiakbar Alijonov",
        "Sherzod Nasrullaev", "Umar Eshmurodov", "Abdukodir Khusanov",
        "Abdulla Abdullaev", "Bekhruz Karimov", "Jakhongir Urozov",
        "Avazbek Ulmasaliev",
        "Otabek Shukurov", "Jaloliddin Masharipov", "Odiljon Hamrobekov",
        "Oston Urunov", "Jamshid Iskanderov", "Dostonbek Khamdamov",
        "Abbosbek Fayzullaev", "Akmal Mozgovoy", "Azizjon Ganiev",
        "Sherzod Esanov",
        "Eldor Shomurodov", "Igor Sergeev", "Azizbek Amonov",
    ]),
    "Colombia": ("Nestor Lorenzo", [
        "Camilo Vargas", "Alvaro Montero", "David Ospina",
        "Davinson Sanchez", "Jhon Lucumi", "Yerry Mina", "Willer Ditta",
        "Daniel Munoz", "Santiago Arias", "Johan Mojica", "Deiver Machado",
        "Richard Rios", "Jefferson Lerma", "Kevin Castano",
        "Juan Camilo Portilla", "Gustavo Puerta", "Jhon Arias",
        "Jorge Carrascal", "Juan Fernando Quintero", "James Rodriguez",
        "Jaminton Campaz",
        "Juan Camilo Hernandez", "Luis Diaz", "Luis Suarez",
        "Carlos Andres Gomez", "Jhon Cordoba",
    ]),

    # ===================== Group L =====================
    "England": ("Thomas Tuchel", [
        "Jordan Pickford", "Dean Henderson", "James Trafford",
        "Reece James", "Ezri Konsa", "Jarell Quansah", "John Stones",
        "Marc Guehi", "Dan Burn", "Nico O'Reilly", "Djed Spence",
        "Tino Livramento",
        "Declan Rice", "Elliot Anderson", "Kobbie Mainoo", "Jordan Henderson",
        "Morgan Rogers", "Jude Bellingham", "Eberechi Eze",
        "Harry Kane", "Ivan Toney", "Ollie Watkins", "Bukayo Saka",
        "Marcus Rashford", "Anthony Gordon", "Noni Madueke",
    ]),
    "Croatia": ("Zlatko Dalic", [
        "Dominik Livakovic", "Dominik Kotarski", "Ivor Pandur",
        "Josko Gvardiol", "Duje Caleta-Car", "Josip Sutalo", "Josip Stanisic",
        "Marin Pongracic", "Martin Erlic", "Luka Vuskovic",
        "Luka Modric", "Mateo Kovacic", "Mario Pasalic", "Nikola Vlasic",
        "Luka Sucic", "Martin Baturina", "Kristijan Jakic", "Petar Sucic",
        "Nikola Moro", "Toni Fruk",
        "Ivan Perisic", "Andrej Kramaric", "Ante Budimir", "Marco Pasalic",
        "Petar Musa", "Igor Matanovic",
    ]),
    "Ghana": ("Carlos Queiroz", [
        "Benjamin Asare", "Lawrence Ati-Zigi", "Joseph Anang",
        "Baba Abdul Rahman", "Gideon Mensah", "Marvin Senaya", "Alidu Seidu",
        "Abdul Mumin", "Jerome Opoku", "Jonas Adjetey", "Kojo Oppong Peprah",
        "Elisha Owusu", "Derrick Luckassen",
        "Thomas Partey", "Kwasi Sibo", "Augustine Boakye", "Caleb Yirenkyi",
        "Abdul Fatawu Issahaku",
        "Kamaldeen Sulemana", "Christopher Bonsu Baah", "Ernest Nuamah",
        "Antoine Semenyo", "Brandon Thomas-Asante", "Prince Kwabena Adu",
        "Inaki Williams", "Jordan Ayew",
    ]),
    "Panama": ("Thomas Christiansen", [
        "Luis Mejia", "Orlando Mosquera", "Cesar Samudio",
        "Eric Davis", "Fidel Escobar", "Michael Amir Murillo",
        "Roderick Miller", "Andres Andrade", "Cesar Blackman", "Jose Cordoba",
        "Jiovany Ramos", "Jorge Gutierrez", "Edgardo Farina",
        "Anibal Godoy", "Alberto Quintero", "Yoel Barcenas",
        "Adalberto Carrasquilla", "Jose Luis Rodriguez", "Cristian Martinez",
        "Cesar Yanis", "Carlos Harvey", "Azarias Londono",
        "Jose Fajardo", "Ismael Diaz", "Cecilio Waterman", "Tomas Rodriguez",
    ]),
}


def load(check_only: bool = False) -> None:
    db.init_db()

    # Cross-check squad keys against the team names that actually appear in
    # fixtures, so a mis-named key (e.g. "Czech Republic") is caught early.
    fixture_teams = {
        t for m in db.list_matches()
        for t in (m["team_a"], m["team_b"])
    }
    unknown = sorted(k for k in SQUADS if k not in fixture_teams)
    missing = sorted(t for t in fixture_teams
                     if t in __import__("teams").FLAGS and t not in SQUADS)

    if unknown:
        print("⚠️  Squad keys not matching any fixture team (check spelling):")
        for k in unknown:
            print(f"     - {k}")
    if missing:
        print("ℹ️  Fixture teams still without a squad in this file:")
        for t in missing:
            print(f"     - {t}")

    if check_only:
        print(f"\n{len(SQUADS)} squads defined · "
              f"{len(SQUADS) - len(unknown)} match a fixture team.")
        return

    for team, (coach, players) in SQUADS.items():
        db.upsert_squad(team, coach, "\n".join(players))

    print(f"✅ Loaded {len(SQUADS)} squads "
          f"({sum(len(p) for _, p in SQUADS.values())} players total).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Seed team squads + coaches.")
    ap.add_argument("--check", action="store_true",
                    help="Validate names against fixtures without writing.")
    args = ap.parse_args()
    load(check_only=args.check)
