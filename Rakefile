require 'erb'
require 'base64'
require 'globby'
require 'open-uri'
require 'octokit'
require 'mail'
require 'yaml'

$config = YAML.load_file('config.yaml') rescue {}

raise "Please configure SendGrid integration" unless $config[:smtp].is_a? Hash
raise "Please go change the SendGrid password now and remove it from the repo" if $config[:smtp].include? :password

$config[:smtp][:password] = ENV['SENDGRID_PASSWORD']
Mail.defaults do
  delivery_method :smtp, $config[:smtp]
end

def sendmail(recipient, subject_line, text, html=nil)
  mail = Mail.new do
    to      recipient
    from    $config[:smtp][:from]
    subject subject_line

    text_part do
        body text
    end

    if html
      html_part do
          content_type 'text/html; charset=UTF-8'
          body html
      end
    end
  end

  if ENV['debug']
    puts mail.to_s
  else
    mail.deliver!
  end
end

def github_client(page_size = 100)
  @token ||= ENV['GITHUB_TOKEN'] || `git config --global github.token`.chomp

  if @token.empty?
    puts "You need to generate a GitHub token:"
    puts "\t * https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line"
    puts "\t * git config --global github.token <token>"
    puts
    puts "Export that as the `GITHUB_TOKEN` environment variable or put it in your ~/.gitconfig."
    exit 1
  end

  begin
    client = Octokit::Client.new(:access_token => @token, per_page: page_size)
  rescue => e
    puts "Github login error: #{e.message}"
    exit 1
  end

  client
end

task :default do
  puts 'This automates several github org housekeeping processes.'
  puts
  system("rake -T")
end

desc 'Generate and send a stale PR report with a sample of the oldest open PRs.'
task :stale_pulls do
  org    = $config[:org]
  stale  = github_client.search_issues("is:pr state:open user:#{org} archived:false sort:created-asc")
  sample = stale[:items].sample(15)

  sendmail(
    ENV['EMAIL_ADDRESS'],
    'Housekeeping report: stale pull requests',
    ERB.new(File.read('templates/stale_prs.txt.erb'), nil, '-').result(binding),
    ERB.new(File.read('templates/stale_prs.html.erb'), nil, '-').result(binding),
  )
end

desc 'Check CODEOWNER coverage for all public repositories'
task :codeowner_coverage do
  org    = $config[:org]
  client = github_client
  client.auto_paginate = true

  owners =      client.org_teams(org).map {|team| "@#{org}/#{team[:slug]}" }
  owners.concat client.org_members(org).map {|user| "@#{user[:login]}" }

  missing   = []
  malformed = []
  coverage  = []
  userowned = []

  repos = client.repos(org).each do |repo|
    begin
      next if repo[:archived]
      next if repo[:fork]
      next if repo[:private]

      sha   = client.commits(repo[:full_name]).first[:sha]
      tree  = client.tree(repo[:full_name], sha, :recursive => true)[:tree]

      files = tree.map {|entry| entry[:path]     if entry[:type] == 'blob' }.compact
      dirs  = tree.map {|entry| entry[:path]+'/' if entry[:type] == 'tree' }.compact  # Globby only matches if directories have the trailing /
      path  = files.find {|f| f =~ /CODEOWNERS/ }
      unless path
        missing << repo
        next
      end

      rules  = []
      errors = []
      users  = []
      Base64.decode64(client.contents(repo[:full_name], :path => path).content).split("\n").each do |line|
        rule, *assignees = line.split
        next unless rule
        next if rule.start_with? '#'
        rules << rule

        teams, usernames = assignees.partition {|assignee| assignee.include? '/'}
        mismatch = (teams - owners)
        errors << "No teams matched rule: #{rule}" if teams.empty?
        errors << "The team(s) #{mismatch.join(',')} appear to be invalid for rule: #{rule}" unless mismatch.empty?

        users.concat usernames
      end

      source = Globby::GlObject.new(files, dirs)
      misses = Globby.reject(rules, source)
      unless misses.empty?
        coverage << repo
      end

      unless errors.empty?
        repo[:codeowner_errors] = errors
        malformed << repo
      end

      unless users.empty?
        repo[:codeowner_users] = users.uniq
        userowned << repo
      end

    rescue => e
      puts "Borked repo [#{repo[:name]}] #{e.message}"
    end
  end

  sendmail(
    ENV['EMAIL_ADDRESS'],
    'Housekeeping report: CODEOWNERS linting',
    ERB.new(File.read('templates/codeowners.txt.erb'), nil, '-').result(binding),
    ERB.new(File.read('templates/codeowners.html.erb'), nil, '-').result(binding),
  )

end

desc 'Generate a report of open PRs from the Support team.'
task :support_pulls do
  org     = $config[:org]
  supteam = $config[:support_team]

  team    = github_client.team_by_name(org, supteam)
  repos   = github_client.team_repositories(team.id)

  pull_requests = repos.reduce([]) do |memo, repo|
    next memo if repo[:archived]

    begin
      codeowners = Base64.decode64(github_client.contents(repo.full_name, :path => 'CODEOWNERS').content)
      next memo unless codeowners.match? (/@#{org}\/#{supteam}/)
    rescue Octokit::NotFound
      # comment this line to make this branch a no-op to include repos with no CODEOWNERS
      next memo
    end

    all_prs = github_client.pull_requests(repo.full_name, :state => 'open')
    memo.concat all_prs.select {|pr| github_client.team_member?(team.id, pr[:user][:login]) }
  end

  sendmail(
    ENV['EMAIL_ADDRESS'],
    'Housekeeping report: open Support team pull requests',
    ERB.new(File.read('templates/support_prs.txt.erb'), nil, '-').result(binding),
    ERB.new(File.read('templates/support_prs.html.erb'), nil, '-').result(binding),
  )
end


desc 'Check inactive contributors in public repositories'
task :inactive_contributors do
  require 'date'
  require 'google/cloud/bigquery'
  require 'set'

  # Known bots that may not appear in collaborator lists.
  exclusions = %w[pdk-bot]

  org    = $config[:org]
  client = github_client
  client.auto_paginate = true

  # Collect repository names and contributors.
  puts "Collecting public repositories for #{org}..."
  repo_names = client.repos(org, type: 'public').reject do |repo|
    repo[:archived] || repo[:fork] || repo[:private]
  end.map {|repo| repo[:full_name]}

  puts "Found #{repo_names.count} public repositories, finding all active GitHub accounts..."
  bigquery = Google::Cloud::Bigquery.new
  today, datefmt = Date.today, "%Y%m"
  # Find all activity for the requested repositories in the last 180 days. We use the BigQuery
  # dataset because requesting events through the GitHub API does at most the last 3 months. This
  # processes approximately 5GB of data through BigQuery.
  sql = "SELECT actor.login FROM `githubarchive.month.*` WHERE _TABLE_SUFFIX "+
    "BETWEEN '#{(today-180).strftime(datefmt)}' AND '#{today.strftime(datefmt)}' "+
    "AND repo.name IN (#{repo_names.map {|s| "'"+s+"'"}.join(',')}) GROUP BY actor.login"
  data = bigquery.query sql do |conf|
    conf.location = "US"
  end
  puts "Found #{data.count} active accounts in #{org} repositories"

  contribs = Set.new
  data.each do |row|
    contribs.add(row[:login])
  end

  inaccessible = []
  repo_names.each do |repo_name|
    # Print collaborators that haven't had any activity in the last 6 months.
    begin
      collabs = client.collabs(repo_name, affiliation: 'outside')
      inactive = collabs.map {|c| c[:login]}.reject {|name| contribs.include?(name)}
      inactive = inactive.reject {|name| exclusions.include?(name)}
      puts "Inactive collaborators in #{repo_name}: #{inactive.join(', ')}" unless inactive.empty?
    rescue Octokit::Forbidden
      inaccessible << repo_name
      STDERR.puts "Insufficient access to list collaborators in #{repo_name}"
    end
  end
  puts "Unable to access #{inaccessible.count} repositories"
end

task :shell do
  require 'pry'
  binding.pry
end
