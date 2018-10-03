var socket = io.connect('http://localhost:5000/chore');

var warningText = document.getElementById('warnings');

window.onload = function(){
	if(warningText.innerHTML == ''){
		warningText.style.display = "none";
	}
	else{
		warningText.style.display = "block";
	}
}

function choreComplete(chore){
	socket.emit('chorecomplete', chore);
}

socket.on('update', function(){
	location.reload();
});