function loaded() {
  flexworkers();
  getData();
  getProjects();
  consolegobrrr();
}
function td(data) {
  const td = document.createElement("td");
  td.innerText = data;
  return td;
}

function flexworkers() {
 fetch("/api/overall_stats").then(res => res.json()).then(data => {
   if(data.projects === 1) {
      document.getElementById("Imsoextra").innerText = "project";
      document.getElementById("Imsoextra1").innerText = "is";
    }
    document.getElementById("projects").innerText = data.projects;
    if(data.workers === 1) {
      document.getElementById("whyamIsoextra").innerText = "person";
      document.getElementById("whyamIsoextra1").innerText = "has";
    }
    document.getElementById("flex").innerText = data.workers;
 });
}
function getData() {
  const table = document.getElementById("Leaderboard");
  fetch("/api/leaderboard").then(res=>res.json()).then(data => {
    //let a = 1;
    let totalTasks=0;
    data.leaderboard.forEach((u, i) => {
        //if(i <= 9) {
          const {name, tasks} = u;
          const tr = document.createElement("tr");
          tr.setAttribute("id", "leaderboard-data")
          tr.append(td(i + 1))
          tr.append(td(name));
          tr.append(td(tasks));
          totalTasks = totalTasks + parseInt(tasks)
          document.getElementById("t").append(tr);
        //}
      });
      document.getElementById("tt").innerText = totalTasks;
  })
}
function getProjects() {
  const table = document.getElementById("Projects");
  fetch("/api/projects/stats").then(res=>res.json()).then(data => {
    data.forEach(i => {
        const { name, percent, x, y } = i;
        const tr = document.createElement("tr");
        tr.append(td(name));
        tr.append(td(parseFloat(percent)+"%"));
        tr.append(td(`(${x}, ${y})`));
        tr.setAttribute("id", "project-data")
        document.getElementById("tableBody").prepend(tr);
    });
  })
}