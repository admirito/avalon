
continuous_flow_prob = 0.3
update_flow_prob = 0.5

ip_range = (0, 0xffffffff)
ip_norm_stddev = 100

port_range = (0, 0xffff)
port_norm_stddev = 20

l4_range = (0, 142)
l4_norm_stddev = 6

l7_range = (0, 2988)
l7_norm_stddev = 20


metadata_count_max = 30
metadata_count_mean = 7
metadata_stddev = 4

default_metadata_values = ['python', 'C', 'java', 'C#', 'javascript', 'rust', 
    'ruby', 'php', 'Go', 'R', 'scala', 'swift',  'cpp', 'prolog', 'VHDL', 
    'perl', 'pascal', 'matlab', 'lua', 'kotlin', 'J', 'html', 'css', 'haskell',
    'fortran', 'F#', 'dart', 'cuda', 'cobol', 'lisp', 'D', 'awk', 'shell', 
    'Ada', 'verilog', 'typescript', 'julia',
    'Don Quixote', 'Pilgrim\'s Progress', 'Robinson Crusoe', 
    'Gulliver\'s Travels', 'Tom Jones', 'Clarissa', 'Tristram Shandy',
    'Dangerous Liaisons', 'Emma', 'Frankenstein', 'Nightmare Abbey', 
    'The Black Sheep', 'The Charterhouse of Parma', 
    'The Count of Monte Cristo', 'Sybil', 'David Copperfield', 
    'Wuthering Heights', 'Jane Eyre', 'Vanity Fair', 'The Scarlet Letter', 
    'Madame Bovary', 'The Woman in White', 'Alice\'s Adventures In Wonderland',
    'Little Women', 'The Way We Live Now', 'Anna Karenina', 'Daniel Deronda', 
    'The Brothers Karamazov', 'The Portrait of a Lady', 'Huckleberry Finn', 
    'The Strange Case of Dr Jekyll and Mr Hyde', 'Three Men in a Boat', 
    'The Picture of Dorian Gray', 'The Diary of a Nobody', 'Jude the Obscure', 
    'The Riddle of the Sands', 'The Call of the Wild', 'Nostromo', 
    'The Wind in the Willows', 'In Search of Lost Time', 'The Rainbow', 
    'The Good Soldier', 'The Thirty-Nine Steps', 'Ulysses', 'Mrs Dalloway', 
    'A Passage to India', 'The Great Gatsby', 'The Trial', 'Men Without Women', 
    'Journey to the End of the Night', 'As I Lay Dying', 'Brave New World', 
    'Scoop', 'USA', 'The Big Sleep', 'The Pursuit Of Love', 'The Plague', 
    'Nineteen Eighty-Four', 'Malone Dies', 'Catcher in the Rye', 'Wise Blood', 
    'Charlotte\'s Web', 'The Lord Of The Rings'
]
# 'metadata-name':listOfValues
metadata_values = {

}
metadata_values_stddev = 3

