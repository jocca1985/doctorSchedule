function get_constraints() {
    var constraints = new Array;
    var constraints_str = localStorage.getItem('constraint');
    if (constraints_str !== null) {
        constraints = JSON.parse(constraints_str); 
    }
    return constraints;
}
 
function add() {
    var doctor = document.getElementById('doctor').value;
    var room = document.getElementById('room').value;
    var constraints = get_constraints();
    constraints.push({"doctor":doctor,"room":room});
    localStorage.setItem('constraint', JSON.stringify(constraints));
 
    show();
    document.getElementById('doctor').value = '';
    document.getElementById('room').value = '';
    room = ''
    return false;
}
 
function remove() {
    var id = this.getAttribute('id');
    var constraints = get_constraints();
    constraints.splice(id, 1);
    localStorage.setItem('constraint', JSON.stringify(constraints));
 
    show();
 
    return false;
}
 
function show() {
    var constraints = get_constraints();
 
    var html = '<ul>';
    for(var i=0; i<constraints.length; i++) {
        html += '<li>' + constraints[i].doctor + ":" + constraints[i].room + '<button class="remove" id="' + i  + '">x</button></li>';
    };
    html += '</ul>';
 
    document.getElementById('results').innerHTML = html;
 
    var buttons = document.getElementsByClassName('remove');
    for (var i=0; i < buttons.length; i++) {
        buttons[i].addEventListener('click', remove);
    };
}

function combine(){
    let data = {"num_rooms":document.getElementById("rooms").value,"num_days": document.getElementById("days").value, "num_doctors":document.getElementById("doctors").value, "constraints":get_constraints()}
    fetch('https://grehv0h888.execute-api.us-east-1.amazonaws.com/stage/combine', {
      method: 'POST', // or 'PUT'
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(result => window.open(result.url))
    .catch((error) => {
      console.log('Error:', error);
    });
}
 

document.getElementById('combine').addEventListener('click', combine); 
document.getElementById('add').addEventListener('click', add);
show();
